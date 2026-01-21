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
    help = 'Importa pacientes desde CSV SOME (optimizado + comuna default 206).'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Ruta del archivo CSV.')

    # ================== LIMPIEZAS ==================

    def limpiar_bool(self, valor):
        if pd.isna(valor) or valor in ('', None):
            return False
        valor = re.sub(r'[^\d]', '', str(valor))
        try:
            return bool(int(valor))
        except Exception:
            return False

    def limpiar_rut(self, valor):
        if pd.isna(valor) or valor is None:
            return ''
        return (
            str(valor)
            .replace('\xa0', '')
            .replace('\u200b', '')
            .replace(' ', '')
            .strip()
        )

    def es_rut_recien_nacido(self, rut):
        if not rut:
            return False
        rut_limpio = re.sub(r'[^\d]', '', rut.split('-')[0])
        try:
            return int(rut_limpio) >= 90000000
        except Exception:
            return False

    def limpiar_texto(self, texto):
        if pd.isna(texto) or texto is None:
            return ''
        texto = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]', '', str(texto))
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto.upper()

    def limpiar_telefono(self, telefono):
        if pd.isna(telefono) or telefono is None:
            return None
        telefono = re.sub(r'[^\d]', '', str(telefono))
        return telefono or None

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

        df = pd.read_csv(
            csv_path,
            dtype=str,
            sep=',',
            encoding='latin1',
            engine='python',
            on_bad_lines='skip'
        )

        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df.columns = df.columns.str.strip()

        total_filas = len(df)
        self.stdout.write(self.style.SUCCESS(f'📊 Registros encontrados: {total_filas:,}'))

        # ================== PRECARGA ==================

        self.stdout.write(self.style.SUCCESS('📥 Precargando datos en memoria...'))

        ruts_existentes = set(Paciente.objects.values_list('rut', flat=True))
        comunas = {c.id: c for c in Comuna.objects.all()}
        previsiones = {p.codigo: p for p in Prevision.objects.all()}
        usuarios_anteriores = {u.rut: u for u in UsuarioAnterior.objects.all()}

        # ---------- COMUNA DEFAULT ----------
        COMUNA_DEFAULT_CODIGO = 206
        comuna_default = comunas.get(COMUNA_DEFAULT_CODIGO)

        if not comuna_default:
            self.stderr.write(
                self.style.ERROR(
                    f'❌ No existe la comuna default código {COMUNA_DEFAULT_CODIGO}'
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f'🏷️ Comuna default aplicada: {comuna_default.nombre} ({COMUNA_DEFAULT_CODIGO})'
            )
        )

        # ================== CONTADORES ==================

        total_creados = 0
        total_omitidos = 0
        total_rn_omitidos = 0
        total_comuna_default = 0

        pacientes_buffer = []
        BATCH_SIZE = 1000

        # ================== MIGRACIÓN ==================

        with transaction.atomic():
            with tqdm(total=total_filas, desc="📋 Importando pacientes", unit="reg") as pbar:
                for _, row in df.iterrows():
                    rut = self.limpiar_rut(row.get('rut'))

                    # ---------- RUT ----------
                    if not rut:
                        pbar.update(1)
                        continue

                    if self.es_rut_recien_nacido(rut):
                        total_rn_omitidos += 1
                        pbar.update(1)
                        continue

                    if rut in ruts_existentes:
                        total_omitidos += 1
                        pbar.update(1)
                        continue

                    # ---------- COMUNA ----------
                    comuna_codigo = self.limpiar_entero(row.get('comuna'))
                    comuna = comunas.get(comuna_codigo)

                    if not comuna:
                        comuna = comuna_default
                        total_comuna_default += 1

                    # ---------- FECHAS ----------
                    fecha_nacimiento = pd.to_datetime(
                        row.get('fecha_nacimiento'),
                        errors='coerce',
                        dayfirst=True
                    )
                    fecha_nacimiento = fecha_nacimiento.date() if pd.notna(fecha_nacimiento) else None

                    fecha_fallecimiento = pd.to_datetime(
                        row.get('fecha_fallecimiento'),
                        errors='coerce',
                        dayfirst=True
                    )
                    fecha_fallecimiento = (
                        fecha_fallecimiento.date()
                        if pd.notna(fecha_fallecimiento) and fecha_fallecimiento.year > 1900
                        else None
                    )

                    paciente = Paciente(
                        rut=rut,
                        id_anterior=self.limpiar_entero(row.get('id_anterior')),
                        nombre=self.limpiar_texto(row.get('nombre')),
                        apellido_paterno=self.limpiar_texto(row.get('apellido_paterno')),
                        apellido_materno=self.limpiar_texto(row.get('apellido_materno')),
                        fecha_nacimiento=fecha_nacimiento,
                        sexo=str(row.get('sexo', '')).strip().upper(),
                        estado_civil=str(row.get('estado_civil', '')).strip().upper(),
                        direccion=str(row.get('direccion', '')).strip().upper(),
                        numero_telefono1=self.limpiar_telefono(row.get('numero_telefono1')),
                        numero_telefono2=self.limpiar_telefono(row.get('numero_telefono2')),
                        comuna=comuna,
                        prevision=previsiones.get(self.limpiar_entero(row.get('prevision'))),
                        nombre_social=self.limpiar_texto(row.get('nombre_social')) or None,
                        nombres_padre=self.limpiar_texto(row.get('nombres_padre')) or None,
                        nombres_madre=self.limpiar_texto(row.get('nombres_madre')) or None,
                        nombre_pareja=self.limpiar_texto(row.get('nombre_pareja')) or None,
                        rut_madre=self.limpiar_rut(row.get('rut_madre')) or None,
                        ocupacion=self.limpiar_texto(row.get('ocupacion')) or None,
                        representante_legal=self.limpiar_texto(row.get('representante_legal')) or None,
                        pasaporte=str(row.get('pasaporte', '')).strip() or None,
                        recien_nacido=self.limpiar_bool(row.get('recien_nacido')),
                        extranjero=self.limpiar_bool(row.get('extranjero')),
                        fallecido=self.limpiar_bool(row.get('fallecido')),
                        fecha_fallecimiento=fecha_fallecimiento,
                        usuario_anterior=usuarios_anteriores.get(
                            self.limpiar_rut(row.get('usuario_anterior'))
                        ),
                    )

                    pacientes_buffer.append(paciente)
                    ruts_existentes.add(rut)
                    total_creados += 1

                    if len(pacientes_buffer) >= BATCH_SIZE:
                        Paciente.objects.bulk_create(
                            pacientes_buffer,
                            ignore_conflicts=True,
                            batch_size=BATCH_SIZE
                        )
                        pacientes_buffer.clear()

                    pbar.update(1)

            if pacientes_buffer:
                Paciente.objects.bulk_create(
                    pacientes_buffer,
                    ignore_conflicts=True,
                    batch_size=BATCH_SIZE
                )

        # ================== RESUMEN ==================

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN FINAL'))
        self.stdout.write(self.style.SUCCESS(f'✅ Creados: {total_creados:,}'))
        self.stdout.write(self.style.WARNING(f'⏭️ Omitidos (ya existían): {total_omitidos:,}'))
        self.stdout.write(self.style.WARNING(f'👶 RN omitidos: {total_rn_omitidos:,}'))
        self.stdout.write(self.style.WARNING(
            f'🏷️ Asignados a comuna 206 (NO INFORMADO): {total_comuna_default:,}'
        ))
        self.stdout.write(self.style.SUCCESS('=' * 60))
