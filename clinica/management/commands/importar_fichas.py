import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from tqdm import tqdm

from clinica.models import Ficha
from establecimientos.models.establecimiento import Establecimiento
from personas.models.pacientes import Paciente
from users.models import User


# python manage.py importar_fichas "C:\Users\Informatica\Desktop\Importacion\ficha.csv"

def normalize_rut(value):
    if value is None:
        return ''
    s = str(value).strip().upper()
    if not s or s in ('NAN', 'NULL'):
        return ''
    s = ''.join(ch for ch in s if ch.isalnum())
    if not s:
        return ''
    cuerpo, dv = s[:-1], s[-1]
    try:
        cuerpo = str(int(cuerpo))
    except Exception:
        pass
    return f"{cuerpo}{dv}"


class Command(BaseCommand):
    help = 'Importa fichas desde CSV con auditoría de omitidas'

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
            na_values=['NULL', 'null', '']
        )

        total_filas = len(df)

        # ================= PREPROCESAMIENTO =================

        df['paciente_rut'] = df['rut'].apply(normalize_rut)
        df['usuario_rut'] = df['usuario'].apply(normalize_rut)
        df['establecimiento'] = pd.to_numeric(df['establecimiento'], errors='coerce')

        df['fecha_mov'] = pd.to_datetime(
            df['fecha_mov'],
            errors='coerce',
            format='%Y-%m-%d %H:%M:%S.%f'
        )

        # ================= CACHÉS =================

        pacientes_dict = {
            normalize_rut(p.rut): p for p in Paciente.objects.all()
        }

        usuarios_dict = {
            normalize_rut(u.username): u for u in User.objects.all()
        }

        establecimientos_dict = {
            e.id: e for e in Establecimiento.objects.all()
        }

        fichas_existentes = set(
            Ficha.objects.values_list(
                'numero_ficha_sistema',
                'establecimiento_id'
            )
        )

        fichas_a_crear = []
        errores = []

        total_importadas = 0
        total_omitidas = 0
        total_duplicadas = 0
        err_paciente = 0
        err_establecimiento = 0

        self.stdout.write(self.style.SUCCESS('🚀 Importando fichas...'))

        with tqdm(total=total_filas, unit='reg') as pbar:
            for idx, row in df.iterrows():

                paciente_rut = row['paciente_rut']
                numero_ficha = str(row['numero_ficha_sistema']).strip()
                est_id = row['establecimiento']

                # ---------- PACIENTE ----------
                if not paciente_rut or paciente_rut not in pacientes_dict:
                    total_omitidas += 1
                    err_paciente += 1
                    errores.append({
                        'fila_csv': idx + 2,
                        'motivo': 'PACIENTE_NO_EXISTE',
                        'rut': row.get('rut'),
                        'numero_ficha': numero_ficha,
                        'establecimiento': est_id,
                    })
                    pbar.update(1)
                    continue

                # ---------- ESTABLECIMIENTO ----------
                if pd.isna(est_id) or int(est_id) not in establecimientos_dict:
                    total_omitidas += 1
                    err_establecimiento += 1
                    errores.append({
                        'fila_csv': idx + 2,
                        'motivo': 'ESTABLECIMIENTO_INVALIDO',
                        'rut': row.get('rut'),
                        'numero_ficha': numero_ficha,
                        'establecimiento': est_id,
                    })
                    pbar.update(1)
                    continue

                clave = (numero_ficha, int(est_id))

                # ---------- DUPLICADOS ----------
                if clave in fichas_existentes:
                    total_omitidas += 1
                    total_duplicadas += 1
                    errores.append({
                        'fila_csv': idx + 2,
                        'motivo': 'DUPLICADA',
                        'rut': row.get('rut'),
                        'numero_ficha': numero_ficha,
                        'establecimiento': est_id,
                    })
                    pbar.update(1)
                    continue

                fichas_existentes.add(clave)

                fecha_mov = None
                if pd.notna(row['fecha_mov']):
                    fecha_mov = timezone.make_aware(row['fecha_mov'])

                ficha = Ficha(
                    numero_ficha_sistema=numero_ficha,
                    paciente=pacientes_dict[paciente_rut],
                    establecimiento=establecimientos_dict[int(est_id)],
                    usuario=usuarios_dict.get(row['usuario_rut']),
                    observacion=str(row['observacion']).strip().upper()
                    if pd.notna(row['observacion']) else '',
                    fecha_mov=fecha_mov
                )

                fichas_a_crear.append(ficha)

                if len(fichas_a_crear) >= batch_size:
                    with transaction.atomic():
                        Ficha.objects.bulk_create(
                            fichas_a_crear,
                            batch_size=batch_size,
                            ignore_conflicts=True
                        )
                    total_importadas += len(fichas_a_crear)
                    fichas_a_crear.clear()

                pbar.update(1)

        if fichas_a_crear:
            with transaction.atomic():
                Ficha.objects.bulk_create(
                    fichas_a_crear,
                    batch_size=batch_size,
                    ignore_conflicts=True
                )
            total_importadas += len(fichas_a_crear)

        # ================= CSV ERRORES =================

        if errores:
            df_err = pd.DataFrame(errores)
            df_err.to_csv(
                'errores_importacion_fichas.csv',
                index=False,
                encoding='utf-8-sig'
            )

        # ================= RESUMEN =================

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN FINAL'))
        self.stdout.write(self.style.SUCCESS(f'✅ Importadas: {total_importadas:,}'))
        self.stdout.write(self.style.WARNING(f'⚠️ Omitidas: {total_omitidas:,}'))
        self.stdout.write(self.style.WARNING(f'🔁 Duplicadas: {total_duplicadas:,}'))
        self.stdout.write(self.style.WARNING(f'👤 Sin paciente: {err_paciente:,}'))
        self.stdout.write(self.style.WARNING(f'🏥 Establecimiento inválido: {err_establecimiento:,}'))
        self.stdout.write(self.style.SUCCESS('📁 CSV: errores_importacion_fichas.csv'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
