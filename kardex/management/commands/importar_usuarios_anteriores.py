import pandas as pd
from django.core.management.base import BaseCommand

from kardex.models import UsuarioAnterior, Establecimiento


class Command(BaseCommand):
    help = 'Importa users anteriores desde una hoja llamada "usuarios_anteriores" en un archivo Excel'

    def add_arguments(self, parser):
        parser.add_argument(
            'excel_path',
            type=str,
            help='Ruta al archivo Excel que contiene la hoja "usuarios_anteriores"'
        )

    def handle(self, *args, **options):
        excel_path = options['excel_path']

        try:
            df = pd.read_excel(excel_path, sheet_name='usuarios_anteriores')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Error al leer el archivo: {e}'))
            return

        total_importados = 0
        total_actualizados = 0

        for index, row in df.iterrows():
            rut = str(row.get('rut', '')).strip()
            nombre = str(row.get('nombre', '')).strip()
            correo = str(row.get('correo', '')).strip()
            establecimiento_id = row.get('establecimiento_id')

            if not all([rut]):
                self.stdout.write(self.style.WARNING(
                    f'⚠️ Fila {index + 2}: Datos obligatorios faltantes. Se omite.'
                ))
                continue

            establecimiento = None
            if pd.notna(establecimiento_id) and establecimiento_id != '':
                try:
                    establecimiento = Establecimiento.objects.filter(id=int(establecimiento_id)).first()
                    if not establecimiento:
                        self.stdout.write(self.style.WARNING(
                            f'⚠️ Fila {index + 2}: Establecimiento con ID {establecimiento_id} no encontrado.'
                        ))
                except ValueError:
                    self.stdout.write(self.style.WARNING(
                        f'⚠️ Fila {index + 2}: ID de establecimiento inválido: {establecimiento_id}.'
                    ))

            obj, created = UsuarioAnterior.objects.update_or_create(
                rut=rut.upper(),
                defaults={
                    'nombre': nombre.upper(),
                    'correo': correo.lower(),
                    'establecimiento': establecimiento
                }
            )

            if created:
                total_importados += 1
            else:
                total_actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Usuarios anteriores procesados: {total_importados} nuevos, {total_actualizados} actualizados.'
        ))
