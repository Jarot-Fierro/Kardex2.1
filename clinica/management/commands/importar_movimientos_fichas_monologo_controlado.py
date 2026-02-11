import os

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from tqdm import tqdm

from clinica.models.ficha import Ficha
from clinica.models.movimiento_ficha_monologo_controlado import MovimientoMonologoControlado
from establecimientos.models.establecimiento import Establecimiento
from establecimientos.models.servicio_clinico import ServicioClinico
from personas.models.pacientes import Paciente
from personas.models.profesionales import Profesional
from personas.models.usuario_anterior import UsuarioAnterior


class Command(BaseCommand):
    help = 'Importa movimientos de fichas monologo controlado desde un archivo Excel.'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str)

    def clean_rut(self, rut):
        if pd.isna(rut):
            return None
        s = str(rut).strip()
        if not s or s.lower() == 'nan':
            return None
        return s.replace('.', '').replace('-', '').upper()

    def format_rut_chilean(self, rut_limpio):
        """
        Formatea un RUT limpio (sin puntos ni guión) al formato chileno (XX.XXX.XXX-X).
        Si el RUT es inválido o muy corto, devuelve el original con guión si es posible.
        """
        if not rut_limpio or len(rut_limpio) < 2:
            return rut_limpio if rut_limpio else ''

        cuerpo = rut_limpio[:-1]
        dv = rut_limpio[-1]

        try:
            # Formatear cuerpo con puntos
            cuerpo_fmt = "{:,}".format(int(cuerpo)).replace(",", ".")
            return f"{cuerpo_fmt}-{dv}"
        except ValueError:
            return f"{cuerpo}-{dv}"

    def clean_obs(self, val):
        """
        Limpia campos de texto/observación. Si es nulo o 'nan', devuelve string vacío.
        """
        if pd.isna(val):
            return ''
        s = str(val).strip()
        if not s or s.lower() in ['nan', 'none', 'null']:
            return ''
        return s

    def parse_date(self, value):
        if pd.isna(value):
            return None

        try:
            dt = pd.to_datetime(value, errors='coerce')
            if pd.isna(dt):
                return None

            dt_py = dt.to_pydatetime()

            # 🔥 Excel usa 1900 como fecha base vacía
            if dt_py.year <= 1900:
                return None

            if timezone.is_naive(dt_py):
                return timezone.make_aware(dt_py)

            return dt_py

        except Exception:
            return None

    def handle(self, *args, **kwargs):

        excel_path = kwargs['excel_file']

        if not os.path.exists(excel_path):
            self.stdout.write(self.style.ERROR('Archivo no existe'))
            return

        self.stdout.write(self.style.SUCCESS(f'Leyendo archivo: {excel_path}'))

        df = pd.read_excel(excel_path)
        df.columns = df.columns.str.strip()
        df.dropna(how='all', inplace=True)  # Descartar filas vacías

        total_rows = len(df)
        self.stdout.write(f'Total registros: {total_rows}')

        # =============================
        # CARGA EN MEMORIA
        # =============================

        pacientes_map = {
            self.clean_rut(r): i
            for r, i in Paciente.objects.values_list('rut', 'id')
            if r
        }

        fichas_map = {
            (num, est): fid
            for num, est, fid in Ficha.objects.values_list(
                'numero_ficha_sistema', 'establecimiento_id', 'id'
            )
        }

        usuarios_map = {
            self.clean_rut(r): i
            for r, i in UsuarioAnterior.objects.values_list('rut', 'id')
            if r
        }

        profesionales_map = {
            self.clean_rut(r): i
            for r, i in Profesional.objects.values_list('rut', 'id')
            if r
        }

        servicios_map = {
            (cod, est): sid
            for cod, est, sid in ServicioClinico.objects.values_list(
                'codigo', 'establecimiento_id', 'id'
            )
        }

        estabs_set = set(
            Establecimiento.objects.values_list('id', flat=True)
        )

        # =============================
        # PROCESAMIENTO
        # =============================

        registros_creados = 0
        errores = 0
        objetos = []

        log = open('log_importacion_debug.txt', 'w', encoding='utf-8')

        for index, row in tqdm(df.iterrows(), total=total_rows, desc='⏳ Importando movimientos', unit='fila'):
            try:
                estab_id = int(row['establecimiento'])

                if estab_id not in estabs_set:
                    raise ValueError(f'Establecimiento {estab_id} no existe')

                # === Extracción de datos con limpieza ===
                raw_rut = row.get('rut_paciente')
                rut_clean = self.clean_rut(raw_rut)
                # Formatear RUT para el campo de texto (XX.XXX.XXX-X)
                rut_texto = self.format_rut_chilean(rut_clean)

                paciente_id = pacientes_map.get(rut_clean)

                ficha_num = int(row['ficha']) if pd.notna(row.get('ficha')) else 0
                ficha_id = fichas_map.get((ficha_num, estab_id))

                usuario_entrega_raw = row.get('usuario_entrega')
                usuario_entrega_clean = self.clean_rut(usuario_entrega_raw)
                usuario_entrega_id = usuarios_map.get(usuario_entrega_clean)
                usuario_entrega_texto = str(usuario_entrega_raw) if pd.notna(usuario_entrega_raw) else None

                usuario_entrada_raw = row.get('usuario_entrada')
                usuario_entrada_clean = self.clean_rut(usuario_entrada_raw)
                usuario_entrada_id = usuarios_map.get(usuario_entrada_clean)
                usuario_entrada_texto = str(usuario_entrada_raw) if pd.notna(usuario_entrada_raw) else None

                profesional_raw = row.get('profesional')
                profesional_clean = self.clean_rut(profesional_raw)
                profesional_fk_id = profesionales_map.get(profesional_clean)
                profesional_texto = str(profesional_raw) if pd.notna(profesional_raw) else None

                servicio_cod = row.get('servicio_clinico')
                servicio_id = None
                if pd.notna(servicio_cod):
                    try:
                        servicio_id = servicios_map.get((int(float(str(servicio_cod))), estab_id))
                    except Exception:
                        servicio_id = None

                estado = str(row.get('estado')).strip().upper()

                if estado not in ['E', 'R']:
                    raise ValueError(f"Estado inválido: {estado}")

                # Fechas pre-parsed (evita parsearlas varias veces)
                fecha_salida_dt = self.parse_date(row.get('fecha_salida'))
                fecha_entrada_dt = self.parse_date(row.get('fecha_entrada'))
                fecha_traspaso_dt = self.parse_date(row.get('fecha_traspaso'))

                # La BD actualmente exige fecha_salida NOT NULL (ver log). Si viene vacía,
                # aplicamos una política segura para no perder filas:
                # 1) Usar fecha_entrada si existe.
                # 2) Si tampoco existe, usar "ahora" (aware) y dejar registro en el log.
                if fecha_salida_dt is None:
                    if fecha_entrada_dt is not None:
                        fecha_salida_dt = fecha_entrada_dt
                        log.write(f'Fila {index + 2}: fecha_salida vacía → se usó fecha_entrada.\n')
                    else:
                        # último recurso: ahora
                        fecha_salida_dt = timezone.now()
                        log.write(f'Fila {index + 2}: fecha_salida y fecha_entrada vacías → se usó NOW().\n')

                mov = MovimientoMonologoControlado(
                    rut=rut_texto,
                    numero_ficha=ficha_num,
                    rut_paciente_id=paciente_id,
                    ficha_id=ficha_id,
                    establecimiento_id=estab_id,
                    servicio_clinico_destino_id=servicio_id,
                    profesional_id=profesional_fk_id,
                    profesional_anterior=profesional_texto,
                    fecha_salida=fecha_salida_dt,
                    fecha_entrada=fecha_entrada_dt,
                    fecha_traspaso=fecha_traspaso_dt,
                    usuario_entrega=usuario_entrega_texto,
                    # OJO: el campo en el modelo se llama `usuario_entrega_id` (ForeignKey),
                    # por lo que el atributo crudo para asignar el ID es `usuario_entrega_id_id`.
                    usuario_entrega_id_id=usuario_entrega_id,
                    usuario_entrada=usuario_entrada_texto,
                    # Igual para `usuario_entrada_id`.
                    usuario_entrada_id_id=usuario_entrada_id,
                    observacion_salida=self.clean_obs(row.get('observacion_salida')),
                    observacion_entrada=self.clean_obs(row.get('observacion_entrada')),
                    observacion_traspaso=self.clean_obs(row.get('observacion_traspaso')),
                    estado=estado
                )

                objetos.append(mov)

                # Insertar en bloques seguros
                if len(objetos) == 500:
                    try:
                        with transaction.atomic():
                            MovimientoMonologoControlado.objects.bulk_create(objetos)
                        registros_creados += len(objetos)
                        objetos = []
                    except Exception as e:
                        # Fallback registro a registro para no perder filas buenas
                        log.write(f'ERROR BULK fila aprox {index}: {str(e)}\n')
                        # Reintentar individualmente
                        ok = 0
                        for obj in objetos:
                            try:
                                with transaction.atomic():
                                    obj.save()
                                ok += 1
                            except Exception as ei:
                                errores += 1
                                log.write(f'  - Error guardando individual: {ei}\n')
                        registros_creados += ok
                        objetos = []

            except Exception as e:
                errores += 1
                log.write(f'Fila {index + 2}: {str(e)}\n')

        # Insertar resto
        if objetos:
            try:
                with transaction.atomic():
                    MovimientoMonologoControlado.objects.bulk_create(objetos)
                registros_creados += len(objetos)
            except Exception as e:
                log.write(f'ERROR BULK FINAL: {str(e)}\n')
                # Fallback final: registro a registro
                ok = 0
                for obj in objetos:
                    try:
                        with transaction.atomic():
                            obj.save()
                        ok += 1
                    except Exception as ei:
                        errores += 1
                        log.write(f'  - Error guardando individual: {ei}\n')
                registros_creados += ok

        log.close()

        self.stdout.write(self.style.SUCCESS(
            f'\nRegistros creados: {registros_creados}'
        ))
        self.stdout.write(self.style.WARNING(
            f'Registros con error: {errores}'
        ))
        self.stdout.write('Revisar log_importacion_debug.txt')
