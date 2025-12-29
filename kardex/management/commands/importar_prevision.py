import pandas as pd
from django.core.management.base import BaseCommand

from kardex.models import Prevision


class Command(BaseCommand):
    help = 'Importa Previsiones desde una hoja llamada "prevision" en un archivo Excel'

    def add_arguments(self, parser):
        parser.add_argument(
            'excel_path',
            type=str,
            help='Ruta al archivo Excel que contiene la hoja "prevision"'
        )

    def handle(self, *args, **options):
        excel_path = options['excel_path']

        try:
            df = pd.read_excel(excel_path, sheet_name='prevision')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Error al leer el archivo: {e}'))
            return

        total_importados = 0
        total_actualizados = 0

        for _, row in df.iterrows():
            nombre = str(row.get('nombre', '')).strip()

            if not nombre:
                continue

            # Guardar o actualizar país
            obj, created = Prevision.objects.update_or_create(
                nombre__iexact=nombre,
                defaults={
                    'nombre': nombre.upper()
                }
            )

            if created:
                total_importados += 1
            else:
                total_actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Importación completada: {total_importados} nuevos, {total_actualizados} actualizados.'
        ))
