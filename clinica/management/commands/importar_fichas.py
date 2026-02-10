import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from tqdm import tqdm

from clinica.models import Ficha
from establecimientos.models.establecimiento import Establecimiento
from establecimientos.models.sectores import Sector
from personas.models.pacientes import Paciente
from personas.models.usuario_anterior import UsuarioAnterior
from users.models import User


# =========================
# COMMAND
# =========================

class Command(BaseCommand):
    help = 'Importa fichas desde Excel (.xlsx) con validación, duplicados y log'

    def add_arguments(self, parser):
        parser.add_argument('excel_path', type=str, help='Ruta del archivo Excel (.xlsx, .xls)')
        parser.add_argument('--sheet', type=str, default=0, help='Nombre o índice de la hoja (por defecto: 0)')
        parser.add_argument('--skiprows', type=int, default=0, help='Filas a saltar al inicio')

    # ================== LIMPIEZAS (Inspiradas en importar_pacientes.py) ==================

    def normalize_rut(self, value):
        if pd.isna(value) or value is None:
            return ''
        # Mantener el formato del modelo Paciente si es posible, o normalizar para búsqueda
        return ''.join(c for c in str(value).upper().strip() if c.isalnum())

    def safe_str(self, value):
        if pd.isna(value) or value is None or str(value).lower() in ('nan', 'none'):
            return ''
        return str(value).strip()

    def limpiar_entero(self, valor):
        if pd.isna(valor) or valor in ('', None, 'None', 'nan', 'NAN', '0', 0):
            return None
        try:
            if isinstance(valor, float):
                if valor.is_integer():
                    return int(valor)
                else:
                    return None
            valor_limpio = str(valor).strip().replace('.0', '')
            if not valor_limpio or valor_limpio in ('None', 'nan', '0'):
                return None
            return int(valor_limpio)
        except Exception:
            return None

    def parse_fecha(self, value):
        if pd.isna(value) or value is None:
            return None

        # Si ya es datetime de pandas
        if isinstance(value, pd.Timestamp):
            if value == pd.Timestamp('1900-01-01'):
                return None
            try:
                return timezone.make_aware(value.to_pydatetime()) if timezone.is_naive(
                    value.to_pydatetime()) else value.to_pydatetime()
            except Exception:
                return value.to_pydatetime()

        value_str = str(value).strip()
        if not value_str or value_str in ('01-01-1900', '1900-01-01', '1900-01-01 00:00:00', '01-01-1900 00:00:00'):
            return None

        # Intentar como número de serie de Excel
        try:
            fecha_num = float(value_str)
            fecha = pd.Timestamp('1899-12-30') + pd.Timedelta(days=fecha_num)
            if fecha == pd.Timestamp('1900-01-01'):
                return None
            dt = fecha.to_pydatetime()
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        except (ValueError, TypeError):
            pass

        dt = parse_datetime(value_str)
        if dt:
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt

        return None

    def handle(self, *args, **options):
        ruta = options['excel_path']
        sheet = options['sheet']
        skiprows = options['skiprows']
        log_lines = []

        self.stdout.write(f'\n📖 Leyendo Excel: {ruta}')

        try:
            df = pd.read_excel(
                ruta,
                sheet_name=sheet,
                skiprows=skiprows,
                dtype=str,
                na_values=['', ' ', 'NaN', 'N/A', 'NULL', 'None'],
                keep_default_na=True
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Error leyendo Excel: {e}'))
            return

        df.columns = df.columns.str.strip().str.lower()

        columnas_requeridas = {
            'establecimiento',
            'paciente',  # este es el RUT en el nuevo formato
            'numero_ficha_sistema',
            'fecha_mov'
        }

        faltantes = columnas_requeridas - set(df.columns)
        if faltantes:
            self.stderr.write(self.style.ERROR(
                f'❌ Columnas faltantes en Excel: {faltantes}'
            ))
            self.stdout.write(f"Columnas detectadas: {list(df.columns)}")
            return

        # =========================
        # CACHÉS
        # =========================

        self.stdout.write('⏳ Precargando datos...')

        pacientes = {
            self.normalize_rut(p.rut): p
            for p in Paciente.objects.all() if p.rut
        }

        establecimientos = {
            e.id: e
            for e in Establecimiento.objects.all()
        }

        sectores_no_informado = {
            s.establecimiento_id: s
            for s in Sector.objects.select_related('color').filter(color__nombre='NO INFORMADO')
        }

        usuarios_anteriores = {
            self.normalize_rut(u.rut): u
            for u in UsuarioAnterior.objects.all() if u.rut
        }

        # Búsqueda de usuarios del sistema por RUT (asumiendo que username puede ser el RUT o similar)
        usuarios_sistema = {
            self.normalize_rut(u.username): u
            for u in User.objects.all()
        }

        fichas_existentes = set(
            Ficha.objects.values_list(
                'numero_ficha_sistema',
                'establecimiento_id'
            )
        )

        fichas_csv = set()

        # =========================
        # CONTADORES
        # =========================

        creadas = 0
        creadas_sin_paciente = 0
        omitidas = 0
        duplicados_insertados = 0
        duplicados = 0
        sin_paciente = 0
        sin_establecimiento = 0
        error_formato = 0
        errores_guardado = 0

        # =========================
        # IMPORTACIÓN
        # =========================

        buffer = []
        BATCH_SIZE = 1000

        self.stdout.write('⏳ Iniciando proceso de importación...')

        with tqdm(total=len(df), desc='⏳ Importando fichas', unit='fila') as pbar:
            for idx, row in df.iterrows():
                fila_excel = idx + 2 + skiprows  # Aproximación

                rut_paciente_raw = row.get('paciente')
                rut_paciente = self.normalize_rut(rut_paciente_raw)
                numero_ficha_raw = row.get('numero_ficha_sistema')
                numero_ficha = self.limpiar_entero(numero_ficha_raw)
                est_raw = row.get('establecimiento')
                est_id = self.limpiar_entero(est_raw)

                # -------- VALIDACIÓN BÁSICA --------
                if numero_ficha is None or est_id is None or not rut_paciente:
                    omitidas += 1
                    error_formato += 1
                    log_lines.append(
                        f'FILA {fila_excel} | ERROR FORMATO | RUT={rut_paciente_raw} | FICHA={numero_ficha_raw} | EST={est_raw}'
                    )
                    pbar.update(1)
                    continue

                paciente = pacientes.get(rut_paciente)
                establecimiento = establecimientos.get(est_id)

                if not establecimiento:
                    omitidas += 1
                    sin_establecimiento += 1
                    log_lines.append(
                        f'FILA {fila_excel} | ESTABLECIMIENTO NO EXISTE | ID={est_id}'
                    )
                    pbar.update(1)
                    continue

                if not paciente:
                    # El usuario indica que si no existe el paciente, se crea igual pero sin paciente asignado
                    # y guardando el rut en rut_anterior
                    sin_paciente += 1
                    # No incrementamos creadas_sin_paciente aquí, lo haremos cuando se guarde exitosamente
                    log_lines.append(
                        f'FILA {fila_excel} | PACIENTE NO EXISTE (Se intentará asignar a RUT Anterior) | RUT={rut_paciente_raw} | FICHA={numero_ficha}'
                    )
                    # No hacemos continue, permitimos que siga para crear la ficha sin paciente

                clave = (numero_ficha, est_id)

                # -------- DUPLICADOS --------
                if clave in fichas_existentes or clave in fichas_csv:
                    # omitidas += 1  <-- Ya no omitimos
                    duplicados += 1
                    duplicados_insertados += 1
                    msg_duplicado = f'FILA {fila_excel} | DUPLICADA (Se ingresará) | RUT={rut_paciente} | FICHA={numero_ficha} | EST={est_id}'
                    log_lines.append(msg_duplicado)
                    # El usuario pidió un mensaje en consola para duplicados
                    self.stdout.write(self.style.WARNING(
                        f'Registro duplicado detectado (se ingresará): RUT {rut_paciente}, Ficha {numero_ficha}, Est. {est_id}'))
                    # pbar.update(1)
                    # continue  <-- Eliminamos el continue para permitir que se cree

                fichas_csv.add(clave)

                # -------- PROCESAR USUARIOS --------
                usuario_raw = row.get('usuario')
                rut_usuario = self.normalize_rut(usuario_raw)

                u_sistema = usuarios_sistema.get(rut_usuario)
                u_anterior = usuarios_anteriores.get(rut_usuario)

                # -------- FECHAS --------
                f_mov = self.parse_fecha(row.get('fecha_mov'))
                f_creacion_ant = self.parse_fecha(row.get('fecha_creacion_anterior'))

                # -------- SECTOR --------
                sector = sectores_no_informado.get(est_id)

                # -------- PREPARAR OBJETO --------
                ficha = Ficha(
                    numero_ficha_sistema=numero_ficha,
                    numero_ficha_tarjeta=numero_ficha,  # Copiar numero_ficha_sistema a numero_ficha_tarjeta
                    paciente=paciente,
                    rut_anterior=rut_paciente_raw if not paciente else 'SIN RUT',
                    establecimiento=establecimiento,
                    sector=sector,
                    usuario=u_sistema,
                    usuario_anterior=u_anterior,
                    observacion=self.safe_str(row.get('observacion')),
                    fecha_mov=f_mov,
                    fecha_creacion_anterior=f_creacion_ant,
                )

                # Si no tiene numero_ficha_sistema, Django intentará generarlo en el save()
                # Pero bulk_create no llama al save(). Para evitar fallos de integridad por null
                # y asegurar que se guardan, usaremos save() directo para los registros sin paciente
                # o si falla el bulk.

                if not paciente:
                    try:
                        with transaction.atomic():
                            ficha.save()
                        creadas_sin_paciente += 1
                        creadas += 1
                    except Exception as e:
                        creadas -= 0  # No sumamos si falla
                        errores_guardado += 1
                        log_lines.append(
                            f'ERROR AL GUARDAR (SIN PACIENTE) | RUT={rut_paciente_raw} | FICHA={numero_ficha} | ERROR={str(e)[:100]}')
                    pbar.update(1)
                    continue

                buffer.append(ficha)
                creadas += 1

                # Guardar en lotes
                if len(buffer) >= BATCH_SIZE:
                    try:
                        with transaction.atomic():
                            Ficha.objects.bulk_create(buffer)
                        buffer.clear()
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'\nError en bulk_create: {str(e)[:100]}'))
                        for f in buffer:
                            try:
                                with transaction.atomic():
                                    f.save()
                            except Exception as e2:
                                creadas -= 1
                                if not f.paciente:
                                    creadas_sin_paciente -= 1
                                errores_guardado += 1
                                log_lines.append(
                                    f'ERROR AL GUARDAR | RUT={f.rut_anterior if not f.paciente else f.paciente.rut} | FICHA={f.numero_ficha_sistema} | ERROR={str(e2)[:100]}')
                        buffer.clear()

                pbar.update(1)

            # Guardar restantes
            if buffer:
                try:
                    with transaction.atomic():
                        Ficha.objects.bulk_create(buffer)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'\nError en último bulk_create: {str(e)[:100]}'))
                    for f in buffer:
                        try:
                            with transaction.atomic():
                                f.save()
                        except Exception as e2:
                            creadas -= 1
                            if not f.paciente:
                                creadas_sin_paciente -= 1
                            errores_guardado += 1
                            log_lines.append(
                                f'ERROR AL GUARDAR | RUT={f.rut_anterior if not f.paciente else f.paciente.rut} | FICHA={f.numero_ficha_sistema} | ERROR={str(e2)[:100]}')
                buffer.clear()

        # =========================
        # LOG TXT
        # =========================

        with open('log_importacion_fichas_excel.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_lines))

        # =========================
        # RESUMEN
        # =========================

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN IMPORTACIÓN'))
        self.stdout.write(self.style.SUCCESS(f'✅ Fichas creadas exitosamente: {creadas}'))
        self.stdout.write(self.style.SUCCESS(f'   - Fichas con paciente vinculado: {creadas - creadas_sin_paciente}'))
        self.stdout.write(self.style.SUCCESS(f'   - Fichas sin paciente (RUT anterior): {creadas_sin_paciente}'))
        self.stdout.write(self.style.SUCCESS(f'   - Duplicados forzados: {duplicados_insertados}'))
        self.stdout.write(self.style.WARNING(f'⚠️ Total Omitidas/Fallidas: {omitidas + errores_guardado}'))
        self.stdout.write(self.style.WARNING(f'🔁 Duplicadas (detectadas en total): {duplicados}'))
        self.stdout.write(self.style.WARNING(f'👤 Paciente no encontrado (encontrados en Excel): {sin_paciente}'))
        self.stdout.write(self.style.WARNING(f'🏥 Establecimiento no encontrado: {sin_establecimiento}'))
        self.stdout.write(self.style.WARNING(f'❌ Error formato datos: {error_formato}'))
        self.stdout.write(self.style.WARNING(f'💾 Errores de guardado BD: {errores_guardado}'))
        self.stdout.write(self.style.SUCCESS('📄 Log generado: log_importacion_fichas_excel.txt'))
        self.stdout.write('=' * 60)
