import pandas as pd
from django.core.management.base import BaseCommand

from kardex.models import Comuna, Establecimiento


class Command(BaseCommand):
    help = 'Importa establecimientos desde una hoja llamada "establecimiento" en un archivo Excel'

    def add_arguments(self, parser):
        parser.add_argument(
            'excel_path',
            type=str,
            help='Ruta al archivo Excel que contiene la hoja "establecimiento"'
        )

    def handle(self, *args, **options):
        excel_path = options['excel_path']

        try:
            df = pd.read_excel(excel_path, sheet_name='establecimiento')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Error al leer el archivo: {e}'))
            return

        total_importadas = 0
        total_actualizadas = 0

        for index, row in df.iterrows():
            nombre = str(row.get('nombre', '')).strip()
            direccion = str(row.get('direccion', '')).strip()
            telefono = str(row.get('telefono', '')).strip()
            comuna_id_raw = row.get('comuna_id')  # OJO: no debe tener espacio al final

            if not nombre:
                self.stdout.write(self.style.WARNING(f'⚠️ Fila {index + 2} sin nombre. Se omite.'))
                continue

            # Validar comuna
            comuna_obj = None
            if pd.notna(comuna_id_raw) and comuna_id_raw != '':
                try:
                    comuna_id = int(comuna_id_raw)
                    comuna_obj = Comuna.objects.filter(id=comuna_id).first()
                    if not comuna_obj:
                        self.stdout.write(self.style.WARNING(
                            f'⚠️ Fila {index + 2}: No se encontró comuna con id={comuna_id}. Fila omitida.'
                        ))
                        continue
                except ValueError:
                    self.stdout.write(self.style.WARNING(
                        f'⚠️ Fila {index + 2}: ID de comuna inválido: {comuna_id_raw}. Fila omitida.'
                    ))
                    continue
            else:
                self.stdout.write(self.style.WARNING(
                    f'⚠️ Fila {index + 2}: comuna_id está vacío o nulo. Fila omitida.'
                ))
                continue

            # Crear o actualizar establecimiento
            obj, created = Establecimiento.objects.update_or_create(
                nombre__iexact=nombre,
                defaults={
                    'nombre': nombre.upper(),
                    'direccion': direccion,
                    'telefono': telefono,
                    'comuna': comuna_obj  # ✅ pasamos el objeto, no el id
                }
            )

            if created:
                total_importadas += 1
            else:
                total_actualizadas += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Importación completada: {total_importadas} nuevas, {total_actualizadas} actualizadas.'
        ))
