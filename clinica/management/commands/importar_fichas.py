import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from tqdm import tqdm

from clinica.models import Ficha
from establecimientos.models.establecimiento import Establecimiento
from personas.models.pacientes import Paciente


# =========================
# HELPERS
# =========================

def normalize_rut(value):
    if pd.isna(value) or value is None:
        return ''
    return ''.join(c for c in str(value).upper().strip() if c.isalnum())


def safe_str(value):
    if pd.isna(value) or value is None:
        return ''
    return str(value).strip()


def parse_fecha(value):
    if pd.isna(value) or value is None:
        return None

    value = str(value).strip()
    if not value:
        return None

    dt = parse_datetime(value)
    if not dt:
        return None

    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt


# =========================
# COMMAND
# =========================

class Command(BaseCommand):
    help = 'Importa fichas desde CSV antiguo con validación, duplicados y log'

    def add_arguments(self, parser):
        parser.add_argument('ruta_csv', type=str)

    def handle(self, *args, **options):
        ruta = options['ruta_csv']
        log_lines = []

        self.stdout.write(f'\n📖 Leyendo CSV: {ruta}')

        df = pd.read_csv(
            ruta,
            sep=',',
            dtype=str,
            encoding='utf-8-sig'
        )

        df.columns = df.columns.str.strip().str.lower()

        columnas_requeridas = {
            'establecimiento',
            'rut',
            'num_nficha',
            'fecha_mov',
            'observacion'
        }

        faltantes = columnas_requeridas - set(df.columns)
        if faltantes:
            self.stderr.write(self.style.ERROR(
                f'❌ Columnas faltantes en CSV: {faltantes}'
            ))
            return

        # =========================
        # CACHÉS
        # =========================

        pacientes = {
            normalize_rut(p.rut): p
            for p in Paciente.objects.all()
        }

        establecimientos = {
            e.id: e
            for e in Establecimiento.objects.all()
        }

        fichas_existentes = set(
            Ficha.objects.values_list(
                'numero_ficha_sistema',
                'establecimiento_id'
            )
        )

        fichas_csv = set()

        # =========================
        # CONTADORES
        # =========================

        creadas = 0
        omitidas = 0
        duplicadas = 0
        sin_paciente = 0
        error_formato = 0

        # =========================
        # IMPORTACIÓN
        # =========================

        with transaction.atomic():
            for idx, row in tqdm(
                    df.iterrows(),
                    total=len(df),
                    desc='⏳ Importando fichas',
                    unit='fila'
            ):
                fila_csv = idx + 2  # considerando encabezado

                rut = normalize_rut(row.get('rut'))
                numero_ficha = safe_str(row.get('num_nficha'))
                est_raw = safe_str(row.get('establecimiento'))

                # -------- VALIDACIÓN BÁSICA --------
                if not numero_ficha or not est_raw.isdigit():
                    omitidas += 1
                    error_formato += 1
                    log_lines.append(
                        f'FILA {fila_csv} | ERROR FORMATO | RUT={rut} | FICHA={numero_ficha}'
                    )
                    continue

                est_id = int(est_raw)
                paciente = pacientes.get(rut)
                establecimiento = establecimientos.get(est_id)

                if not paciente:
                    omitidas += 1
                    sin_paciente += 1
                    log_lines.append(
                        f'FILA {fila_csv} | PACIENTE NO EXISTE | RUT={rut} | FICHA={numero_ficha}'
                    )
                    continue

                if not establecimiento:
                    omitidas += 1
                    error_formato += 1
                    log_lines.append(
                        f'FILA {fila_csv} | ESTABLECIMIENTO INVÁLIDO | ID={est_raw}'
                    )
                    continue

                clave = (numero_ficha, est_id)

                # -------- DUPLICADOS --------
                if clave in fichas_existentes or clave in fichas_csv:
                    omitidas += 1
                    duplicadas += 1
                    log_lines.append(
                        f'FILA {fila_csv} | DUPLICADA | RUT={rut} | FICHA={numero_ficha} | EST={est_id}'
                    )
                    continue

                fichas_csv.add(clave)

                # -------- CREAR FICHA --------
                Ficha.objects.create(
                    numero_ficha_sistema=numero_ficha,
                    paciente=paciente,
                    establecimiento=establecimiento,
                    usuario=None,
                    observacion=safe_str(row.get('observacion')),
                    fecha_mov=parse_fecha(row.get('fecha_mov')),
                )

                fichas_existentes.add(clave)
                creadas += 1

        # =========================
        # LOG TXT
        # =========================

        with open('log_importacion_fichas.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_lines))

        # =========================
        # RESUMEN
        # =========================

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN IMPORTACIÓN'))
        self.stdout.write(self.style.SUCCESS(f'✅ Fichas creadas: {creadas}'))
        self.stdout.write(self.style.WARNING(f'⚠️ Omitidas: {omitidas}'))
        self.stdout.write(self.style.WARNING(f'🔁 Duplicadas: {duplicadas}'))
        self.stdout.write(self.style.WARNING(f'👤 Sin paciente: {sin_paciente}'))
        self.stdout.write(self.style.WARNING(f'❌ Error formato: {error_formato}'))
        self.stdout.write(self.style.SUCCESS('📄 Log generado: log_importacion_fichas.txt'))
        self.stdout.write('=' * 60)
