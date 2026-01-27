import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import make_aware
from tqdm import tqdm

from clinica.models import Ficha, MovimientoFicha
from establecimientos.models.establecimiento import Establecimiento
from establecimientos.models.servicio_clinico import ServicioClinico
from personas.models.profesionales import Profesional
from personas.models.usuario_anterior import UsuarioAnterior


# ================= UTILIDADES =================

def normalize_rut(value):
    if value is None:
        return ''
    s = str(value).strip().upper()
    if not s or s in ('NAN', 'NULL', 'SIN RUT', '0', '0.0'):
        return ''
    # Eliminar puntos, guiones y espacios
    s = s.replace('.', '').replace('-', '').replace(' ', '')
    return s


def clean_text(value):
    if value is None:
        return ''
    s = str(value).strip()
    if s.upper() in ('NAN', 'NULL', 'NONE'):
        return ''
    return s


def safe_make_aware(dt):
    """Convertir datetime a aware de forma segura, manejando NaT"""
    if pd.isna(dt) or dt is None:
        return None
    try:
        return make_aware(dt)
    except (ValueError, AttributeError):
        return None


# ================= COMMAND =================

class Command(BaseCommand):
    help = 'Importa movimientos de fichas desde CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str)
        parser.add_argument('--batch-size', type=int, default=1000)

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        batch_size = options['batch_size']

        self.stdout.write(self.style.SUCCESS(f'📖 Leyendo CSV: {csv_path}'))

        # 🔥 FIX IMPORTANTE PARA CSV SUCIO
        df = pd.read_csv(
            csv_path,
            sep=',',
            dtype=str,
            engine='python',
            quotechar='"',
            on_bad_lines='skip',
            keep_default_na=False
        )

        df.columns = df.columns.str.strip()
        total_filas = len(df)

        self.stdout.write(self.style.SUCCESS(f'📊 Total de filas en CSV: {total_filas:,}'))
        self.stdout.write(self.style.SUCCESS(f'📋 Columnas encontradas: {", ".join(df.columns.tolist())}'))

        # ================= PREPROCESAMIENTO =================

        # Normalizar RUTs
        for rut_col in ['rut_paciente', 'usuario_entrega', 'usuario_entrada', 'profesional']:
            if rut_col in df.columns:
                df[rut_col] = df[rut_col].apply(normalize_rut)

        # Convertir números
        numeric_columns = ['establecimiento', 'ficha', 'servicio_clinico']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Convertir fechas
        if 'fecha_salida' in df.columns:
            df['fecha_salida'] = pd.to_datetime(
                df['fecha_salida'],
                errors='coerce',
                format='mixed'  # Acepta diferentes formatos
            )
            # Filtrar fechas inválidas
            invalid_dates = df['fecha_salida'].isna().sum()
            if invalid_dates > 0:
                self.stdout.write(self.style.WARNING(f'⚠️ Fechas de salida inválidas: {invalid_dates}'))

        if 'fecha_entrada' in df.columns:
            df['fecha_entrada'] = pd.to_datetime(
                df['fecha_entrada'],
                errors='coerce',
                format='mixed'
            )
            invalid_dates = df['fecha_entrada'].isna().sum()
            if invalid_dates > 0:
                self.stdout.write(self.style.WARNING(f'⚠️ Fechas de entrada inválidas: {invalid_dates}'))

        # ================= CACHÉS =================

        self.stdout.write(self.style.SUCCESS('📦 Cargando datos de referencia...'))

        # Cargar fichas
        fichas_dict = {
            (f.numero_ficha_sistema, f.establecimiento_id): f
            for f in Ficha.objects.all()
        }
        self.stdout.write(self.style.SUCCESS(f'✅ Fichas cargadas: {len(fichas_dict):,}'))

        # Cargar establecimientos
        establecimientos_dict = {e.id: e for e in Establecimiento.objects.all()}
        self.stdout.write(self.style.SUCCESS(f'✅ Establecimientos cargados: {len(establecimientos_dict):,}'))

        # Cargar servicios clínicos
        servicios_dict = {s.id: s for s in ServicioClinico.objects.all()}
        self.stdout.write(self.style.SUCCESS(f'✅ Servicios clínicos cargados: {len(servicios_dict):,}'))

        # Cargar usuarios anteriores
        usuarios_ant_dict = {normalize_rut(u.rut): u for u in UsuarioAnterior.objects.all()}
        self.stdout.write(self.style.SUCCESS(f'✅ Usuarios anteriores cargados: {len(usuarios_ant_dict):,}'))

        # Cargar profesionales
        profesionales_dict = {normalize_rut(p.rut): p for p in Profesional.objects.all()}
        self.stdout.write(self.style.SUCCESS(f'✅ Profesionales cargados: {len(profesionales_dict):,}'))

        # Obtener movimientos existentes para evitar duplicados
        movimientos_existentes = set(
            MovimientoFicha.objects.values_list('ficha_id', 'fecha_envio')
        )
        self.stdout.write(self.style.SUCCESS(f'✅ Movimientos existentes: {len(movimientos_existentes):,}'))

        movimientos_a_crear = []
        errores = []

        total_importados = 0
        total_omitidos = 0
        total_duplicados = 0
        total_errores = 0

        self.stdout.write(self.style.SUCCESS('🚀 Importando movimientos...'))

        with tqdm(total=total_filas, unit='reg', desc='Procesando') as pbar:
            for idx, row in df.iterrows():
                try:
                    # Obtener datos básicos
                    ficha_num = row.get('ficha')
                    est_id = row.get('establecimiento')

                    # Verificar que tenemos los datos necesarios
                    if pd.isna(ficha_num) or pd.isna(est_id):
                        total_omitidos += 1
                        errores.append({
                            'fila_csv': idx + 2,
                            'motivo': 'DATOS_INCOMPLETOS',
                            'ficha': ficha_num,
                            'establecimiento': est_id
                        })
                        pbar.update(1)
                        continue

                    # Buscar ficha
                    ficha = fichas_dict.get((int(ficha_num), int(est_id)))
                    if not ficha:
                        total_omitidos += 1
                        errores.append({
                            'fila_csv': idx + 2,
                            'motivo': 'FICHA_NO_EXISTE',
                            'ficha': ficha_num,
                            'establecimiento': est_id
                        })
                        pbar.update(1)
                        continue

                    # Fecha de envío (con manejo seguro)
                    fecha_envio = safe_make_aware(row.get('fecha_salida'))

                    # Verificar duplicado
                    clave = (ficha.id, fecha_envio)
                    if clave in movimientos_existentes:
                        total_omitidos += 1
                        total_duplicados += 1
                        pbar.update(1)
                        continue

                    movimientos_existentes.add(clave)

                    # ================= LÓGICA DE ESTADOS =================

                    # Obtener estado del CSV
                    estado_csv = clean_text(row.get('estado', '')).upper()

                    # Lógica según tu descripción:
                    # - Si estado es 'E' (Enviado): solo llenar datos de envío
                    # - Si estado es 'R' (Recibido): llenar datos de envío Y recepción (copiando los mismos)
                    # - Por defecto: considerar como enviado

                    recibido = estado_csv == 'R'
                    enviado = estado_csv == 'E' or not recibido  # Si no es 'R', es enviado

                    # ================= OBTENER DATOS DE REFERENCIA =================

                    # Establecimiento
                    establecimiento = establecimientos_dict.get(int(est_id))

                    # Servicio clínico (si existe en el CSV)
                    servicio_id = row.get('servicio_clinico')
                    servicio = None
                    if not pd.isna(servicio_id):
                        try:
                            servicio = servicios_dict.get(int(servicio_id))
                        except (ValueError, TypeError):
                            servicio = None

                    # Usuarios anteriores
                    usuario_envio_ant = usuarios_ant_dict.get(normalize_rut(row.get('usuario_entrega', '')))
                    usuario_recep_ant = usuarios_ant_dict.get(normalize_rut(row.get('usuario_entrada', '')))

                    # Profesional
                    profesional = profesionales_dict.get(normalize_rut(row.get('profesional', '')))

                    # ================= CONFIGURAR CAMPOS SEGÚN ESTADO =================

                    # Campos para envío (siempre se llenan si está enviado)
                    estado_envio_final = 'ENVIADO' if enviado else ''
                    servicio_envio_final = servicio if enviado else None
                    profesional_envio_final = profesional if enviado else None
                    usuario_envio_ant_final = usuario_envio_ant if enviado else None

                    # Campos para recepción (solo si está recibido)
                    estado_recepcion_final = 'RECIBIDO' if recibido else 'EN ESPERA'
                    servicio_recepcion_final = servicio if recibido else None
                    profesional_recepcion_final = profesional if recibido else None
                    usuario_recepcion_ant_final = usuario_recep_ant if recibido else None

                    # Fechas
                    fecha_recepcion = None
                    if recibido:
                        fecha_recepcion = safe_make_aware(row.get('fecha_entrada'))
                        # Si no hay fecha de entrada pero sí está recibido, usar fecha de salida
                        if not fecha_recepcion:
                            fecha_recepcion = fecha_envio

                    # ================= CREAR MOVIMIENTO =================

                    movimiento = MovimientoFicha(
                        # Datos básicos
                        ficha=ficha,
                        establecimiento=establecimiento,

                        # Datos de envío
                        fecha_envio=fecha_envio,
                        estado_envio=estado_envio_final,
                        servicio_clinico_envio=servicio_envio_final,
                        profesional_envio=profesional_envio_final,
                        usuario_envio_anterior=usuario_envio_ant_final,
                        observacion_envio=clean_text(row.get('observacion_salida', '')),

                        # Datos de recepción
                        fecha_recepcion=fecha_recepcion,
                        estado_recepcion=estado_recepcion_final,
                        servicio_clinico_recepcion=servicio_recepcion_final,
                        profesional_recepcion=profesional_recepcion_final,
                        usuario_recepcion_anterior=usuario_recepcion_ant_final,
                        observacion_recepcion=clean_text(row.get('observacion_entrada', '')),

                        # Datos de traspaso (siempre sin traspaso en esta importación)
                        estado_traspaso='SIN TRASPASO',
                        observacion_traspaso=clean_text(row.get('observacion_traspaso', '')),

                        # RUTs antiguos (para auditoría)
                        rut_anterior=normalize_rut(row.get('rut_paciente', '')) or 'SIN RUT',
                        rut_anterior_profesional=normalize_rut(row.get('profesional', '')) or 'SIN RUT'
                    )

                    movimientos_a_crear.append(movimiento)

                    # Insertar en lote
                    if len(movimientos_a_crear) >= batch_size:
                        try:
                            with transaction.atomic():
                                MovimientoFicha.objects.bulk_create(movimientos_a_crear, ignore_conflicts=True)
                            total_importados += len(movimientos_a_crear)
                            movimientos_a_crear.clear()
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'❌ Error en batch: {str(e)}'))
                            total_errores += len(movimientos_a_crear)
                            movimientos_a_crear.clear()

                except Exception as e:
                    total_errores += 1
                    errores.append({
                        'fila_csv': idx + 2,
                        'motivo': f'ERROR_GENERAL: {str(e)}',
                        'ficha': row.get('ficha', ''),
                        'establecimiento': row.get('establecimiento', '')
                    })

                pbar.update(1)

        # Insertar los registros restantes
        if movimientos_a_crear:
            try:
                with transaction.atomic():
                    MovimientoFicha.objects.bulk_create(movimientos_a_crear, ignore_conflicts=True)
                total_importados += len(movimientos_a_crear)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error en último batch: {str(e)}'))
                total_errores += len(movimientos_a_crear)

        # Guardar errores si los hay
        if errores:
            error_df = pd.DataFrame(errores)
            error_path = 'errores_importacion_movimientos.csv'
            error_df.to_csv(error_path, index=False, encoding='utf-8-sig')
            self.stdout.write(self.style.WARNING(f'⚠️ Se guardaron {len(errores):,} errores en: {error_path}'))

        # Mostrar resumen
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN FINAL'))
        self.stdout.write(self.style.SUCCESS(f'✅ Importados: {total_importados:,}'))
        self.stdout.write(self.style.WARNING(f'⚠️ Omitidos: {total_omitidos:,}'))
        self.stdout.write(self.style.WARNING(f'🔁 Duplicados: {total_duplicados:,}'))
        self.stdout.write(self.style.ERROR(f'❌ Errores: {total_errores:,}'))

        if total_importados > 0:
            self.stdout.write(self.style.SUCCESS(
                f'📈 Tasa de éxito: {(total_importados / (total_importados + total_omitidos + total_errores) * 100):.1f}%'))

        self.stdout.write(self.style.SUCCESS('=' * 60))

        # Mostrar distribución de estados
        self.stdout.write(self.style.SUCCESS('\n📋 DISTRIBUCIÓN DE ESTADOS:'))
        movimientos_importados = MovimientoFicha.objects.order_by('-id')[:total_importados]
        estados = movimientos_importados.values_list('estado_recepcion', flat=True)

        from collections import Counter
        estado_counter = Counter(estados)
        for estado, count in estado_counter.items():
            self.stdout.write(self.style.SUCCESS(f'  {estado}: {count:,}'))
