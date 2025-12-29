import pandas as pd
from django.core.management.base import BaseCommand

from kardex.models import ServicioClinico, Establecimiento


def _to_str_or_empty(value):
    """Convierte el valor a string sin espacios o retorna '' si viene vacío/NaN/null."""
    if value is None:
        return ''
    try:
        # pandas NaN
        if pd.isna(value):
            return ''
    except Exception:
        pass
    s = str(value).strip()
    if s.lower() in ('nan', 'none', 'null'):
        return ''
    return s


def _to_int_or_none(value):
    """Convierte el valor a int; si viene vacío/NaN/'' retorna None."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, str):
        v = value.strip()
        if v == '' or v.lower() in ('nan', 'none', 'null'):
            return None
        try:
            return int(float(v))
        except Exception:
            return None
    if isinstance(value, (int,)):
        return int(value)
    if isinstance(value, float):
        try:
            return int(value)
        except Exception:
            return None
    # Cualquier otro tipo, intentamos conversión genérica
    try:
        return int(float(str(value).strip()))
    except Exception:
        return None


class Command(BaseCommand):
    help = 'Importa servicios clínicos desde una hoja llamada "servicio_clinico" en un archivo Excel'

    def add_arguments(self, parser):
        parser.add_argument(
            'excel_path',
            type=str,
            help='Ruta al archivo Excel que contiene la hoja "servicio_clinico"'
        )

    def handle(self, *args, **options):
        excel_path = options['excel_path']

        try:
            df = pd.read_excel(excel_path, sheet_name='servicio_clinico')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Error al leer el archivo: {e}'))
            return

        df.columns = df.columns.str.strip()  # Eliminar espacios en los nombres de columnas

        total_importados = 0
        total_actualizados = 0

        for index, row in df.iterrows():
            nombre = _to_str_or_empty(row.get('nombre', ''))
            tiempo_horas = _to_int_or_none(row.get('tiempo_horas'))
            correo_jefe = _to_str_or_empty(row.get('correo_jefe', '')).lower()
            telefono = _to_str_or_empty(row.get('telefono', ''))
            establecimiento_id_raw = row.get('establecimiento_id')

            if not nombre:
                self.stdout.write(self.style.WARNING(
                    f'⚠️ Fila {index + 2} sin nombre. Se omite.'
                ))
                continue

            # Buscar establecimiento
            establecimiento_obj = None
            if establecimiento_id_raw is not None and _to_str_or_empty(establecimiento_id_raw) != '':
                try:
                    establecimiento_id = int(float(str(establecimiento_id_raw).strip()))
                    establecimiento_obj = Establecimiento.objects.filter(id=establecimiento_id).first()
                    if not establecimiento_obj:
                        self.stdout.write(self.style.WARNING(
                            f'⚠️ Fila {index + 2}: Establecimiento ID {establecimiento_id} no encontrado.'
                        ))
                except Exception:
                    self.stdout.write(self.style.WARNING(
                        f'⚠️ Fila {index + 2}: Establecimiento ID inválido: {establecimiento_id_raw}.'
                    ))

            # Logs de depuración para campos potencialmente vacíos o convertidos
            if tiempo_horas is None:
                _style = self.style.NOTICE if hasattr(self.style, 'NOTICE') else self.style.WARNING
                self.stdout.write(_style(f'ℹ️ Fila {index + 2}: tiempo_horas vacío o inválido, se guardará como None.'))
            if correo_jefe == '':
                _style = self.style.NOTICE if hasattr(self.style, 'NOTICE') else self.style.WARNING
                self.stdout.write(_style(f'ℹ️ Fila {index + 2}: correo_jefe vacío.'))
            if telefono == '':
                _style = self.style.NOTICE if hasattr(self.style, 'NOTICE') else self.style.WARNING
                self.stdout.write(_style(f'ℹ️ Fila {index + 2}: teléfono vacío.'))

            # CORRECCIÓN: Buscar por nombre Y establecimiento
            # Esto permite que servicios con el mismo nombre pero en diferentes establecimientos
            # se creen como registros separados
            if establecimiento_obj:
                # Buscar servicio con el mismo nombre Y mismo establecimiento
                obj, created = ServicioClinico.objects.update_or_create(
                    nombre=nombre.upper(),
                    establecimiento=establecimiento_obj,  # Incluir establecimiento en la búsqueda
                    defaults={
                        'tiempo_horas': tiempo_horas,
                        'correo_jefe': correo_jefe,
                        'telefono': telefono
                    }
                )
            else:
                # Si no hay establecimiento, buscar solo por nombre
                obj, created = ServicioClinico.objects.update_or_create(
                    nombre=nombre.upper(),
                    establecimiento__isnull=True,  # Buscar servicios sin establecimiento
                    defaults={
                        'tiempo_horas': tiempo_horas,
                        'correo_jefe': correo_jefe,
                        'telefono': telefono,
                        'establecimiento': None
                    }
                )

            if created:
                total_importados += 1
                est_txt = f", establecimiento_id={establecimiento_obj.id}" if establecimiento_obj else ""
                self.stdout.write(self.style.SUCCESS(
                    f"➕ Fila {index + 2}: creado ServicioClinico id={obj.id}, nombre={obj.nombre}{est_txt}."
                ))
            else:
                total_actualizados += 1
                est_txt = f", establecimiento_id={establecimiento_obj.id}" if establecimiento_obj else ""
                # Log claro para depurar cuáles fueron actualizados
                notice_style = getattr(self.style, 'NOTICE', self.style.WARNING)
                self.stdout.write(notice_style(
                    f"✏️ Fila {index + 2}: actualizado ServicioClinico id={obj.id}, nombre={obj.nombre}{est_txt}."
                ))

        self.stdout.write(self.style.SUCCESS(
            f'✅ Importación completada: {total_importados} nuevos, {total_actualizados} actualizados.'
        ))
