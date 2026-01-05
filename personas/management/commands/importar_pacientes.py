import re

import pandas as pd
from django.core.management.base import BaseCommand
from tqdm import tqdm

from geografia.models.comuna import Comuna
from personas.models.pacientes import Paciente
from personas.models.prevision import Prevision
from personas.models.usuario_anterior import UsuarioAnterior


class Command(BaseCommand):
    help = 'Importa pacientes desde un archivo CSV.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Ruta del archivo CSV.')

    def limpiar_rut(self, valor):
        if pd.isna(valor):
            return ''
        if isinstance(valor, float):
            valor = int(valor)
        rut = str(valor).strip()
        rut = rut.replace('\xa0', '').replace('\u200b', '').replace(' ', '')
        return rut

    def es_rut_recien_nacido(self, rut):
        if not rut:
            return False

        rut_limpio = rut.split('-')[0] if '-' in rut else rut
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
            return ''
        telefono = str(telefono).strip()
        return re.sub(r'[^\d]', '', telefono)

    def limpiar_entero(self, valor):
        """
        Convierte valores tipo '12', '12.0', float o string a int seguro
        """
        if pd.isna(valor) or valor is None or valor == '':
            return None
        try:
            return int(float(valor))
        except (ValueError, TypeError):
            return None

    def handle(self, *args, **options):
        csv_path = options['csv_path']

        try:
            self.stdout.write(self.style.SUCCESS(f'📖 Leyendo archivo CSV: {csv_path}'))

            df = pd.read_csv(
                csv_path,
                dtype=str,
                sep=';',
                engine='python',
                encoding='latin1',
                quotechar='"',
            )

            total_filas = len(df)
            self.stdout.write(self.style.SUCCESS(f'📊 Total de registros encontrados: {total_filas:,}'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Error al leer el CSV: {e}'))
            return

        df.columns = df.columns.str.strip()

        total_creados = 0
        total_actualizados = 0
        total_recien_nacidos_omitidos = 0
        total_errores = 0

        with tqdm(total=total_filas, desc="📋 Procesando pacientes", unit="registro") as pbar:
            for index, row in df.iterrows():
                try:
                    rut = self.limpiar_rut(row.get('rut', ''))

                    if self.es_rut_recien_nacido(rut):
                        total_recien_nacidos_omitidos += 1
                        pbar.update(1)
                        continue

                    # 👉 NUEVO: capturar id_anterior
                    id_anterior = self.limpiar_entero(row.get('id_anterior'))

                    nombre = self.limpiar_texto(row.get('nombre', ''))
                    apellido_paterno = self.limpiar_texto(row.get('apellido_paterno', ''))
                    apellido_materno = self.limpiar_texto(row.get('apellido_materno', ''))
                    direccion = str(row.get('direccion', '')).strip().upper() if pd.notna(row.get('direccion')) else ''

                    numero_telefono1 = self.limpiar_telefono(row.get('numero_telefono1', ''))
                    numero_telefono2 = self.limpiar_telefono(row.get('numero_telefono2', ''))

                    sexo = str(row.get('sexo', '')).strip().upper()
                    estado_civil = str(row.get('estado_civil', '')).strip().upper()

                    fecha_nacimiento = pd.to_datetime(row.get('fecha_nacimiento'), errors='coerce')
                    fecha_nacimiento = fecha_nacimiento.date() if pd.notna(fecha_nacimiento) else None

                    comuna_id = row.get('comuna_id')
                    prevision_id = row.get('prevision_id')
                    genero = str(row.get('genero', '')).strip().upper() or 'NO INFORMADO'

                    usuario_anterior_rut = self.limpiar_rut(row.get('usuario_anterior_id', ''))
                    usuario_anterior = (
                        UsuarioAnterior.objects.filter(rut=usuario_anterior_rut).first()
                        if usuario_anterior_rut else None
                    )

                    rut_madre = self.limpiar_rut(row.get('rut_madre', ''))
                    nombre_social = self.limpiar_texto(row.get('nombre_social', ''))
                    pasaporte = str(row.get('pasaporte', '')).strip().upper()
                    nombres_padre = self.limpiar_texto(row.get('nombres_padre', ''))
                    nombres_madre = self.limpiar_texto(row.get('nombres_madre', ''))
                    nombre_pareja = self.limpiar_texto(row.get('nombre_pareja', ''))
                    representante_legal = self.limpiar_texto(row.get('representante_legal', ''))
                    ocupacion = self.limpiar_texto(row.get('ocupacion', ''))
                    rut_responsable_temporal = self.limpiar_rut(row.get('rut_responsable_temporal', ''))

                    sin_telefono = bool(int(row.get('sin_telefono', '0') or 0))
                    recien_nacido = bool(int(row.get('recien_nacido', '0') or 0))
                    extranjero = bool(int(row.get('extranjero', '0') or 0))
                    fallecido = bool(int(row.get('fallecido', '0') or 0))
                    usar_rut_madre = bool(int(row.get('usar_rut_madre_como_responsable', '0') or 0))

                    fecha_fallecimiento = pd.to_datetime(row.get('fecha_fallecimiento'), errors='coerce')
                    fecha_fallecimiento = fecha_fallecimiento.date() if pd.notna(fecha_fallecimiento) else None

                    if not all([rut, nombre, sexo, estado_civil, comuna_id]):
                        total_errores += 1
                        pbar.update(1)
                        continue

                    comuna = Comuna.objects.filter(id=int(float(comuna_id))).first()
                    if not comuna:
                        total_errores += 1
                        pbar.update(1)
                        continue

                    prevision = None
                    if prevision_id:
                        prevision = Prevision.objects.filter(id=int(float(prevision_id))).first()

                    datos_paciente = {
                        'id_anterior': id_anterior,  # 👈 NUEVO
                        'nombre': nombre,
                        'apellido_paterno': apellido_paterno,
                        'apellido_materno': apellido_materno,
                        'fecha_nacimiento': fecha_nacimiento,
                        'sexo': sexo,
                        'estado_civil': estado_civil,
                        'direccion': direccion,
                        'numero_telefono1': numero_telefono1 or None,
                        'numero_telefono2': numero_telefono2 or None,
                        'comuna': comuna,
                        'prevision': prevision,
                        'genero': genero,
                        'nombre_social': nombre_social or None,
                        'pasaporte': pasaporte or None,
                        'nombres_padre': nombres_padre or None,
                        'nombres_madre': nombres_madre or None,
                        'nombre_pareja': nombre_pareja or None,
                        'representante_legal': representante_legal or None,
                        'ocupacion': ocupacion or None,
                        'rut_madre': rut_madre or None,
                        'rut_responsable_temporal': rut_responsable_temporal or None,
                        'sin_telefono': sin_telefono,
                        'recien_nacido': recien_nacido,
                        'extranjero': extranjero,
                        'fallecido': fallecido,
                        'usuario_anterior': usuario_anterior,
                        'fecha_fallecimiento': fecha_fallecimiento,
                        'usar_rut_madre_como_responsable': usar_rut_madre
                    }

                    paciente, created = Paciente.objects.update_or_create(
                        rut=rut,
                        defaults=datos_paciente
                    )

                    total_creados += int(created)
                    total_actualizados += int(not created)

                except Exception as e:
                    total_errores += 1
                    self.stdout.write(self.style.ERROR(f'❌ Error fila {index + 2}: {e}'))

                pbar.update(1)
                pbar.set_postfix({
                    'Creados': total_creados,
                    'Actualizados': total_actualizados,
                    'RN Omitidos': total_recien_nacidos_omitidos,
                    'Errores': total_errores
                })

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN FINAL'))
        self.stdout.write(self.style.SUCCESS(f'✅ Creados: {total_creados:,}'))
        self.stdout.write(self.style.SUCCESS(f'🔄 Actualizados: {total_actualizados:,}'))
        self.stdout.write(self.style.WARNING(f'👶 RN omitidos: {total_recien_nacidos_omitidos:,}'))
        self.stdout.write(self.style.ERROR(f'❌ Errores: {total_errores:,}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
