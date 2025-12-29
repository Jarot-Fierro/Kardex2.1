import pandas as pd
from django.core.management.base import BaseCommand

from kardex.models import Profesional, Profesion, Establecimiento


class Command(BaseCommand):
    help = 'Importa profesionales desde una hoja llamada "profesional" en un archivo Excel'

    def add_arguments(self, parser):
        parser.add_argument(
            'excel_path',
            type=str,
            help='Ruta al archivo Excel que contiene la hoja "profesional"'
        )

    def handle(self, *args, **options):
        excel_path = options['excel_path']

        try:
            df = pd.read_excel(excel_path, sheet_name='profesional')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Error al leer el archivo: {e}'))
            return

        df.columns = df.columns.str.strip()  # eliminar espacios en nombres de columnas

        total_importados = 0
        total_actualizados = 0

        for index, row in df.iterrows():
            rut = str(row.get('rut', '')).strip()
            nombres = str(row.get('nombres', '')).strip()
            correo = str(row.get('correo', '')).strip()
            anexo = str(row.get('anexo', '')).strip()
            telefono = str(row.get('telefono', '')).strip()
            profesion_id_raw = row.get('profesion_id')
            establecimiento_id_raw = row.get('establecimiento_id')

            if not rut or not nombres or not correo:
                self.stdout.write(self.style.WARNING(
                    f'⚠️ Fila {index + 2} sin rut, nombre o correo. Se omite.'
                ))
                continue

            # Buscar profesión
            profesion_obj = None
            if pd.notna(profesion_id_raw) and profesion_id_raw != '':
                try:
                    profesion_id = int(profesion_id_raw)
                    profesion_obj = Profesion.objects.filter(id=profesion_id).first()
                    if not profesion_obj:
                        self.stdout.write(self.style.WARNING(
                            f'⚠️ Fila {index + 2}: Profesión ID {profesion_id} no encontrada.'
                        ))
                except ValueError:
                    self.stdout.write(self.style.WARNING(
                        f'⚠️ Fila {index + 2}: Profesión ID inválido: {profesion_id_raw}.'
                    ))

            # Buscar establecimiento
            establecimiento_obj = None
            if pd.notna(establecimiento_id_raw) and establecimiento_id_raw != '':
                try:
                    establecimiento_id = int(establecimiento_id_raw)
                    establecimiento_obj = Establecimiento.objects.filter(id=establecimiento_id).first()
                    if not establecimiento_obj:
                        self.stdout.write(self.style.WARNING(
                            f'⚠️ Fila {index + 2}: Establecimiento ID {establecimiento_id} no encontrado.'
                        ))
                except ValueError:
                    self.stdout.write(self.style.WARNING(
                        f'⚠️ Fila {index + 2}: Establecimiento ID inválido: {establecimiento_id_raw}.'
                    ))

            # Crear o actualizar profesional
            obj, created = Profesional.objects.update_or_create(
                rut=rut.upper(),
                defaults={
                    'nombres': nombres.upper(),
                    'correo': correo.lower(),
                    'anexo': anexo,
                    'telefono': telefono,
                    'profesion': profesion_obj,
                    'establecimiento': establecimiento_obj
                }
            )

            if created:
                total_importados += 1
            else:
                total_actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Importación completada: {total_importados} nuevos, {total_actualizados} actualizados.'
        ))
