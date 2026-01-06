import re

import pandas as pd
from django.core.management.base import BaseCommand
from tqdm import tqdm

from geografia.models.comuna import Comuna
from personas.models.pacientes import Paciente
from personas.models.prevision import Prevision
from personas.models.usuario_anterior import UsuarioAnterior


class Command(BaseCommand):
    help = 'Importa pacientes desde un archivo CSV SOME.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Ruta del archivo CSV.')

    # ================== LIMPIEZAS ==================

    def limpiar_bool(self, valor):
        """
        Convierte valores SOME a boolean seguro
        Acepta: 1, 0, '1', '0', NaN, '', basura
        """
        if pd.isna(valor) or valor in ('', None):
            return False

        valor = str(valor).strip()

        # quitar basura tipo ;;;;;;0;;;;
        valor = re.sub(r'[^\d]', '', valor)

        if valor == '':
            return False

        try:
            return bool(int(valor))
        except Exception:
            return False

    def limpiar_rut(self, valor):
        if pd.isna(valor) or valor is None:
            return ''
        rut = str(valor).strip()
        rut = rut.replace('\xa0', '').replace('\u200b', '').replace(' ', '')
        return rut

    def es_rut_recien_nacido(self, rut):
        if not rut:
            return False
        rut_limpio = rut.split('-')[0]
        rut_limpio = re.sub(r'[^\d]', '', rut_limpio)
        try:
            return int(rut_limpio) >= 90000000
        except Exception:
            return False

    def limpiar_texto(self, texto):
        if pd.isna(texto) or texto is None:
            return ''
        texto = str(texto).strip()
        texto = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]', '', texto)
        texto = re.sub(r'\s+', ' ', texto)
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

        try:
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

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Error al leer CSV: {e}'))
            return

        total_creados = 0
        total_actualizados = 0
        total_rn_omitidos = 0
        total_errores = 0

        with tqdm(total=total_filas, desc="📋 Importando pacientes", unit="reg") as pbar:
            for index, row in df.iterrows():
                try:
                    rut = self.limpiar_rut(row.get('rut'))
                    if self.es_rut_recien_nacido(rut):
                        total_rn_omitidos += 1
                        pbar.update(1)
                        continue

                    id_anterior = self.limpiar_entero(row.get('id_anterior'))

                    nombre = self.limpiar_texto(row.get('nombre'))
                    apellido_paterno = self.limpiar_texto(row.get('apellido_paterno'))
                    apellido_materno = self.limpiar_texto(row.get('apellido_materno'))

                    sexo = str(row.get('sexo', '')).strip().upper()
                    estado_civil = str(row.get('estado_civil', '')).strip().upper()

                    fecha_nacimiento = pd.to_datetime(
                        row.get('fecha_nacimiento'),
                        errors='coerce',
                        dayfirst=True
                    )
                    fecha_nacimiento = fecha_nacimiento.date() if pd.notna(fecha_nacimiento) else None

                    direccion = str(row.get('direccion', '')).strip().upper()

                    telefono1 = self.limpiar_telefono(row.get('numero_telefono1'))
                    telefono2 = self.limpiar_telefono(row.get('numero_telefono2'))

                    # ---------- COMUNA ----------
                    comuna_codigo = self.limpiar_entero(row.get('comuna'))
                    comuna = Comuna.objects.filter(codigo=comuna_codigo).first()
                    if not comuna:
                        total_errores += 1
                        pbar.update(1)
                        continue

                    # ---------- PREVISIÓN ----------
                    prevision_codigo = self.limpiar_entero(row.get('prevision'))
                    prevision = Prevision.objects.filter(codigo=prevision_codigo).first() if prevision_codigo else None

                    # ---------- USUARIO ANTERIOR ----------
                    usuario_anterior_rut = self.limpiar_rut(row.get('usuario_anterior'))
                    usuario_anterior = (
                        UsuarioAnterior.objects.filter(rut=usuario_anterior_rut).first()
                        if usuario_anterior_rut else None
                    )

                    fecha_fallecimiento = pd.to_datetime(
                        row.get('fecha_fallecimiento'),
                        errors='coerce',
                        dayfirst=True
                    )
                    fecha_fallecimiento = fecha_fallecimiento.date() if (
                            pd.notna(fecha_fallecimiento) and fecha_fallecimiento.year > 1900
                    ) else None

                    datos = {
                        'id_anterior': id_anterior,
                        'nombre': nombre,
                        'apellido_paterno': apellido_paterno,
                        'apellido_materno': apellido_materno,
                        'fecha_nacimiento': fecha_nacimiento,
                        'sexo': sexo,
                        'estado_civil': estado_civil,
                        'direccion': direccion,
                        'numero_telefono1': telefono1,
                        'numero_telefono2': telefono2,
                        'comuna': comuna,
                        'prevision': prevision,
                        'nombre_social': self.limpiar_texto(row.get('nombre_social')) or None,
                        'nombres_padre': self.limpiar_texto(row.get('nombres_padre')) or None,
                        'nombres_madre': self.limpiar_texto(row.get('nombres_madre')) or None,
                        'nombre_pareja': self.limpiar_texto(row.get('nombre_pareja')) or None,
                        'rut_madre': self.limpiar_rut(row.get('rut_madre')) or None,
                        'ocupacion': self.limpiar_texto(row.get('ocupacion')) or None,
                        'representante_legal': self.limpiar_texto(row.get('representante_legal')) or None,
                        'pasaporte': str(row.get('pasaporte', '')).strip() or None,
                        'recien_nacido': self.limpiar_bool(row.get('recien_nacido')),
                        'extranjero': self.limpiar_bool(row.get('extranjero')),
                        'fallecido': self.limpiar_bool(row.get('fallecido')),
                        'fecha_fallecimiento': fecha_fallecimiento,
                        'usuario_anterior': usuario_anterior,
                    }

                    paciente, created = Paciente.objects.update_or_create(
                        rut=rut,
                        defaults=datos
                    )

                    total_creados += int(created)
                    total_actualizados += int(not created)

                except Exception as e:
                    total_errores += 1
                    self.stdout.write(self.style.ERROR(f'❌ Fila {index + 2}: {e}'))

                pbar.update(1)

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN FINAL'))
        self.stdout.write(self.style.SUCCESS(f'✅ Creados: {total_creados:,}'))
        self.stdout.write(self.style.SUCCESS(f'🔄 Actualizados: {total_actualizados:,}'))
        self.stdout.write(self.style.WARNING(f'👶 RN omitidos: {total_rn_omitidos:,}'))
        self.stdout.write(self.style.ERROR(f'❌ Errores: {total_errores:,}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
