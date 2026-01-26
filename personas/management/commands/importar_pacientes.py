# python manage.py importar_pacientes "C:\Users\jarot\Desktop\Exportacion\paciente.csv"

import csv
import re

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from tqdm import tqdm

from geografia.models.comuna import Comuna
from personas.models.pacientes import Paciente
from personas.models.prevision import Prevision
from personas.models.usuario_anterior import UsuarioAnterior


class Command(BaseCommand):
    help = 'Importa pacientes desde CSV SOME (incluye RN + captura líneas malas).'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Ruta del archivo CSV.')

    # ================== LIMPIEZAS ==================

    def limpiar_bool(self, valor):
        if pd.isna(valor) or valor in ('', None):
            return False
        return str(valor).strip().lower() in ('1', 'true', 't', 'yes', 'y')

    def limpiar_rut(self, valor):
        if pd.isna(valor) or valor is None:
            return ''
        return (
            str(valor)
            .replace('\xa0', '')
            .replace('\u200b', '')
            .replace(' ', '')
            .strip()
            .upper()
        )

    def limpiar_texto(self, texto):
        if pd.isna(texto) or texto is None:
            return ''
        texto = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]', ' ', str(texto))
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto.upper()

    def limpiar_telefono(self, telefono):
        if pd.isna(telefono) or telefono is None:
            return None
        telefono = re.sub(r'[^\d]', '', str(telefono))
        return telefono[:30] or None

    def limpiar_entero(self, valor):
        if pd.isna(valor) or valor in ('', None):
            return None
        try:
            return int(float(valor))
        except Exception:
            return None

    # ================== MAIN ==================

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        self.stdout.write(self.style.SUCCESS(f'📖 Leyendo CSV: {csv_path}'))

        lineas_malas = []

        def bad_line_handler(bad_line):
            lineas_malas.append({
                'contenido': ','.join(bad_line),
                'columnas_detectadas': len(bad_line)
            })
            return None

        df = pd.read_csv(
            csv_path,
            dtype=str,
            sep=',',
            encoding='latin1',
            engine='python',
            on_bad_lines=bad_line_handler
        )

        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df.columns = df.columns.str.strip()

        total_csv = sum(1 for _ in open(csv_path, encoding='latin1')) - 1
        total_leidas = len(df)

        self.stdout.write(self.style.SUCCESS(
            f'📊 CSV real: {total_csv:,} | Leídas: {total_leidas:,}'
        ))

        # ================== GUARDAR LÍNEAS MALAS ==================

        if lineas_malas:
            malas_path = 'pacientes_lineas_malas.csv'
            with open(malas_path, 'w', newline='', encoding='latin1') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['columnas_detectadas', 'contenido']
                )
                writer.writeheader()
                for linea in lineas_malas:
                    writer.writerow(linea)

            self.stdout.write(self.style.WARNING(
                f'⚠️ Líneas malas detectadas: {len(lineas_malas):,}'
            ))
            self.stdout.write(self.style.WARNING(
                f'📄 Guardadas en: {malas_path}'
            ))

        # ================== PRECARGA ==================

        ruts_existentes = set(Paciente.objects.values_list('rut', flat=True))
        comunas = {c.id: c for c in Comuna.objects.all()}
        previsiones = {p.codigo: p for p in Prevision.objects.all()}
        usuarios_anteriores = {u.rut: u for u in UsuarioAnterior.objects.all()}

        COMUNA_DEFAULT = comunas.get(206)
        if not COMUNA_DEFAULT:
            self.stderr.write(self.style.ERROR('❌ No existe comuna default 206'))
            return

        # ================== CONTADORES ==================

        creados = 0
        omitidos = 0
        rn_creados = 0
        comuna_default_count = 0

        buffer = []
        BATCH = 1000

        # ================== IMPORTACIÓN ==================

        with transaction.atomic():
            with tqdm(total=total_leidas, desc='📋 Importando pacientes', unit='reg') as pbar:
                for _, row in df.iterrows():
                    rut = self.limpiar_rut(row.get('cod_rutpac'))

                    if not rut:
                        pbar.update(1)
                        continue

                    if rut in ruts_existentes:
                        omitidos += 1
                        pbar.update(1)
                        continue

                    comuna = comunas.get(self.limpiar_entero(row.get('cod_comuna')))
                    if not comuna:
                        comuna = COMUNA_DEFAULT
                        comuna_default_count += 1

                    fecha_nacimiento = pd.to_datetime(
                        row.get('fec_nacimi'),
                        errors='coerce'
                    )
                    fecha_nacimiento = (
                        fecha_nacimiento.date()
                        if pd.notna(fecha_nacimiento)
                        else None
                    )

                    paciente = Paciente(
                        rut=rut,
                        nombre=self.limpiar_texto(row.get('nom_nombre')),
                        apellido_paterno=self.limpiar_texto(row.get('nom_apepat')),
                        apellido_materno=self.limpiar_texto(row.get('nom_apemat')),
                        fecha_nacimiento=fecha_nacimiento,
                        sexo=str(row.get('ind_tisexo', '')).strip().upper(),
                        direccion=str(row.get('nom_direcc', '')).strip().upper(),
                        numero_telefono1=self.limpiar_telefono(row.get('num_telefo1')),
                        numero_telefono2=self.limpiar_telefono(row.get('num_telefo2')),
                        comuna=comuna,
                        prevision=previsiones.get(self.limpiar_entero(row.get('prevision'))),
                        recien_nacido=self.limpiar_bool(row.get('recien_nacido')),
                        usuario_anterior=usuarios_anteriores.get(
                            self.limpiar_rut(row.get('usuario'))
                        ),
                    )

                    if paciente.recien_nacido:
                        rn_creados += 1

                    buffer.append(paciente)
                    ruts_existentes.add(rut)
                    creados += 1

                    if len(buffer) >= BATCH:
                        Paciente.objects.bulk_create(
                            buffer,
                            batch_size=BATCH,
                            ignore_conflicts=True
                        )
                        buffer.clear()

                    pbar.update(1)

            if buffer:
                Paciente.objects.bulk_create(
                    buffer,
                    batch_size=BATCH,
                    ignore_conflicts=True
                )

        # ================== RESUMEN ==================

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN FINAL'))
        self.stdout.write(self.style.SUCCESS(f'📄 CSV real: {total_csv:,}'))
        self.stdout.write(self.style.SUCCESS(f'📥 Leídas: {total_leidas:,}'))
        self.stdout.write(self.style.WARNING(f'⚠️ Líneas malas: {len(lineas_malas):,}'))
        self.stdout.write(self.style.SUCCESS(f'✅ Creados: {creados:,}'))
        self.stdout.write(self.style.WARNING(f'⏭️ Omitidos: {omitidos:,}'))
        self.stdout.write(self.style.SUCCESS(f'👶 RN creados: {rn_creados:,}'))
        self.stdout.write(self.style.WARNING(
            f'🏷️ Comuna default 206: {comuna_default_count:,}'
        ))
        self.stdout.write(self.style.SUCCESS('=' * 60))
