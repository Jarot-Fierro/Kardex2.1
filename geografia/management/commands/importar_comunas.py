import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from tqdm import tqdm

from geografia.models.comuna import Comuna


# python manage.py importar_comunas "C:\Users\jarot\Desktop\Exportacion\comuna.csv"
class Command(BaseCommand):
    help = 'Importa comunas desde CSV (cod_comuna, nom_comuna)'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str)
        parser.add_argument('--batch-size', type=int, default=1000)

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        batch_size = options['batch_size']

        self.stdout.write(self.style.SUCCESS(f'📖 Leyendo CSV: {csv_path}'))

        df = pd.read_csv(
            csv_path,
            sep=',',
            dtype=str,
            encoding='utf-16'
        )

        # Normalizar encabezados
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace('\ufeff', '', regex=False)
        )

        columnas = set(df.columns)

        if not {'cod_comuna', 'nom_comuna'}.issubset(columnas):
            self.stderr.write(self.style.ERROR(
                f'❌ Columnas esperadas: cod_comuna, nom_comuna'
            ))
            self.stderr.write(self.style.ERROR(
                f'📌 Columnas encontradas: {list(df.columns)}'
            ))
            return

        total_filas = len(df)

        # Preprocesamiento
        df['cod_comuna'] = df['cod_comuna'].fillna('').astype(str).str.strip()
        df['nom_comuna'] = (
            df['nom_comuna']
            .fillna('')
            .astype(str)
            .str.strip()
            .str.upper()
        )

        comunas_existentes = set(
            Comuna.objects.values_list('nombre', flat=True)
        )

        comunas_a_crear = []
        errores = []

        total_importadas = 0
        total_omitidas = 0
        total_duplicadas = 0

        self.stdout.write(self.style.SUCCESS('🚀 Importando comunas...'))

        with tqdm(total=total_filas, unit='reg') as pbar:
            for idx, row in df.iterrows():

                codigo = row['cod_comuna']
                nombre = row['nom_comuna']

                if not nombre:
                    total_omitidas += 1
                    errores.append({
                        'fila_csv': idx + 2,
                        'motivo': 'NOMBRE_VACIO',
                        'codigo': codigo,
                        'nombre': nombre,
                    })
                    pbar.update(1)
                    continue

                if nombre in comunas_existentes:
                    total_omitidas += 1
                    total_duplicadas += 1
                    errores.append({
                        'fila_csv': idx + 2,
                        'motivo': 'COMUNA_DUPLICADA',
                        'codigo': codigo,
                        'nombre': nombre,
                    })
                    pbar.update(1)
                    continue

                comunas_existentes.add(nombre)

                comunas_a_crear.append(
                    Comuna(
                        nombre=nombre,
                        codigo=codigo
                    )
                )

                if len(comunas_a_crear) >= batch_size:
                    with transaction.atomic():
                        Comuna.objects.bulk_create(
                            comunas_a_crear,
                            batch_size=batch_size,
                            ignore_conflicts=True
                        )
                    total_importadas += len(comunas_a_crear)
                    comunas_a_crear.clear()

                pbar.update(1)

        if comunas_a_crear:
            with transaction.atomic():
                Comuna.objects.bulk_create(
                    comunas_a_crear,
                    batch_size=batch_size,
                    ignore_conflicts=True
                )
            total_importadas += len(comunas_a_crear)

        if errores:
            pd.DataFrame(errores).to_csv(
                'errores_importacion_comunas.csv',
                index=False,
                encoding='utf-8-sig'
            )

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN FINAL'))
        self.stdout.write(self.style.SUCCESS(f'✅ Importadas: {total_importadas:,}'))
        self.stdout.write(self.style.WARNING(f'⚠️ Omitidas: {total_omitidas:,}'))
        self.stdout.write(self.style.WARNING(f'🔁 Duplicadas: {total_duplicadas:,}'))
        self.stdout.write(self.style.SUCCESS('📁 CSV: errores_importacion_comunas.csv'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
