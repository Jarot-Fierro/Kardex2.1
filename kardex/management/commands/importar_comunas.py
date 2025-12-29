import pandas as pd
from django.core.management.base import BaseCommand

from kardex.models import Comuna, Pais


class Command(BaseCommand):
    help = 'Importa comunas desde una hoja llamada "comuna" en un archivo Excel'

    def add_arguments(self, parser):
        parser.add_argument(
            'excel_path',
            type=str,
            help='Ruta al archivo Excel que contiene la hoja "comuna"'
        )

    def handle(self, *args, **options):
        excel_path = options['excel_path']

        try:
            df = pd.read_excel(excel_path, sheet_name='comuna')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Error al leer el archivo: {e}'))
            return

        total_importadas = 0
        total_actualizadas = 0

        pais, _ = Pais.objects.get_or_create(nombre='Chile', defaults={'cod_pais': 'CL'})

        for index, row in df.iterrows():
            nombre = str(row.get('nombre', '')).strip()
            codigo = str(row.get('codigo', '')).strip()
            pais_id_raw = row.get('pais_id')

            if not nombre:
                self.stdout.write(self.style.WARNING(f'⚠️ Fila {index + 2} sin nombre. Se omite.'))
                continue

            pais_obj = None
            if pd.notna(pais_id_raw) and pais_id_raw != '':
                try:
                    pais_id = int(pais_id_raw)
                    pais_obj = Pais.objects.filter(id=pais_id).first()
                    if not pais_obj:
                        self.stdout.write(self.style.WARNING(
                            f'⚠️ Fila {index + 2}: No se encontró país con id={pais_id}.'
                        ))
                except ValueError:
                    self.stdout.write(self.style.WARNING(
                        f'⚠️ Fila {index + 2}: ID de país inválido: {pais_id_raw}.'
                    ))

            obj, created = Comuna.objects.update_or_create(
                nombre__iexact=nombre,
                defaults={
                    'nombre': nombre.upper(),
                    'codigo': codigo,
                    'pais': pais_obj  # ✅ O usa pais_id=pais_obj.id si prefieres
                }
            )

            if created:
                total_importadas += 1
            else:
                total_actualizadas += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Importación completada: {total_importadas} nuevas, {total_actualizadas} actualizadas.'
        ))
