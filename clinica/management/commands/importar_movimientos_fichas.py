import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import make_aware
from tqdm import tqdm

from clinica.models import Ficha, MovimientoFicha
from establecimientos.models.establecimiento import Establecimiento
from establecimientos.models.servicio_clinico import ServicioClinico
from personas.models.profesionales import Profesional
from personas.models.usuario_anterior import UsuarioAnterior


def normalize_rut(value):
    if value is None:
        return ''
    s = str(value).strip().upper()
    if not s or s in ('NAN', 'NULL', 'SIN RUT', '0'):
        return ''
    return ''.join(ch for ch in s if ch.isalnum())


class Command(BaseCommand):
    help = 'Importa movimientos de fichas desde CSV con auditoría de omitidos'

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

        df.columns = df.columns.str.strip()
        total_filas = len(df)

        # ================= PREPROCESAMIENTO =================

        df['rut_paciente'] = df['rut_paciente'].apply(normalize_rut)
        df['usuario_entrega'] = df['usuario_entrega'].apply(normalize_rut)
        df['usuario_entrada'] = df['usuario_entrada'].apply(normalize_rut)
        df['profesional'] = df['profesional'].apply(normalize_rut)

        df['establecimiento'] = pd.to_numeric(df['establecimiento'], errors='coerce')
        df['ficha'] = pd.to_numeric(df['ficha'], errors='coerce')
        df['servicio_clinico'] = pd.to_numeric(df['servicio_clinico'], errors='coerce')

        df['fecha_salida'] = pd.to_datetime(df['fecha_salida'], errors='coerce')
        df['fecha_entrada'] = pd.to_datetime(df['fecha_entrada'], errors='coerce')

        # ================= CACHÉS =================

        fichas_dict = {
            (f.numero_ficha_sistema, f.establecimiento_id): f
            for f in Ficha.objects.all()
        }

        establecimientos_dict = {e.id: e for e in Establecimiento.objects.all()}
        servicios_dict = {s.id: s for s in ServicioClinico.objects.all()}
        usuarios_ant_dict = {normalize_rut(u.rut): u for u in UsuarioAnterior.objects.all()}
        profesionales_dict = {normalize_rut(p.rut): p for p in Profesional.objects.all()}

        movimientos_existentes = set(
            MovimientoFicha.objects.values_list(
                'ficha_id',
                'fecha_envio'
            )
        )

        movimientos_a_crear = []
        errores = []

        total_importados = 0
        total_omitidos = 0
        total_duplicados = 0

        self.stdout.write(self.style.SUCCESS('🚀 Importando movimientos...'))

        with tqdm(total=total_filas, unit='reg') as pbar:
            for idx, row in df.iterrows():

                ficha_num = row['ficha']
                est_id = row['establecimiento']

                # ---------- VALIDAR FICHA ----------
                ficha = fichas_dict.get((ficha_num, est_id))
                if not ficha:
                    total_omitidos += 1
                    errores.append({
                        'fila_csv': idx + 2,
                        'motivo': 'FICHA_NO_EXISTE',
                        'ficha': ficha_num,
                        'establecimiento': est_id
                    })
                    pbar.update(1)
                    continue

                fecha_envio = None
                if pd.notna(row['fecha_salida']):
                    fecha_envio = make_aware(row['fecha_salida'])

                clave = (ficha.id, fecha_envio)

                # ---------- DUPLICADO ----------
                if clave in movimientos_existentes:
                    total_omitidos += 1
                    total_duplicados += 1
                    errores.append({
                        'fila_csv': idx + 2,
                        'motivo': 'MOVIMIENTO_DUPLICADO',
                        'ficha': ficha_num,
                        'establecimiento': est_id
                    })
                    pbar.update(1)
                    continue

                movimientos_existentes.add(clave)

                # ---------- RELACIONES ----------
                establecimiento = establecimientos_dict.get(est_id)
                servicio = servicios_dict.get(row['servicio_clinico'])
                usuario_envio = usuarios_ant_dict.get(row['usuario_entrega'])
                usuario_recepcion = usuarios_ant_dict.get(row['usuario_entrada'])
                profesional = profesionales_dict.get(row['profesional'])

                # ---------- ESTADO ----------
                estado = row['estado'].upper() if row['estado'] else 'EN ESPERA'

                # ---------- FECHAS ----------
                fecha_recepcion = make_aware(row['fecha_entrada']) if pd.notna(row['fecha_entrada']) else None

                movimiento = MovimientoFicha(
                    ficha=ficha,
                    establecimiento=establecimiento,
                    fecha_envio=fecha_envio,
                    fecha_recepcion=fecha_recepcion,
                    usuario_envio_anterior=usuario_envio,
                    usuario_recepcion_anterior=usuario_recepcion,
                    profesional_recepcion=profesional,
                    servicio_clinico_recepcion=servicio,
                    observacion_envio=row.get('observacion_salida', ''),
                    observacion_recepcion=row.get('observacion_entrada', ''),
                    observacion_traspaso=row.get('observacion_traspaso', ''),
                    estado_envio='ENVIADO',
                    estado_recepcion=estado,
                    estado_traspaso='SIN TRASPASO',
                    rut_anterior=row.get('rut_paciente', 'SIN RUT'),
                    rut_anterior_profesional=row.get('profesional', 'SIN RUT')
                )

                movimientos_a_crear.append(movimiento)

                if len(movimientos_a_crear) >= batch_size:
                    with transaction.atomic():
                        MovimientoFicha.objects.bulk_create(movimientos_a_crear)
                    total_importados += len(movimientos_a_crear)
                    movimientos_a_crear.clear()

                pbar.update(1)

        if movimientos_a_crear:
            with transaction.atomic():
                MovimientoFicha.objects.bulk_create(movimientos_a_crear)
            total_importados += len(movimientos_a_crear)

        # ================= CSV ERRORES =================

        if errores:
            pd.DataFrame(errores).to_csv(
                'errores_importacion_movimientos.csv',
                index=False,
                encoding='utf-8-sig'
            )

        # ================= RESUMEN =================

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN FINAL'))
        self.stdout.write(self.style.SUCCESS(f'✅ Importados: {total_importados:,}'))
        self.stdout.write(self.style.WARNING(f'⚠️ Omitidos: {total_omitidos:,}'))
        self.stdout.write(self.style.WARNING(f'🔁 Duplicados: {total_duplicados:,}'))
        self.stdout.write(self.style.SUCCESS('📁 CSV: errores_importacion_movimientos.csv'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
