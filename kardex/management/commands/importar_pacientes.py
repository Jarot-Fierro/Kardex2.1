import re

import pandas as pd
from django.core.management.base import BaseCommand
from tqdm import tqdm

from kardex.models import Paciente, Comuna, Prevision, UsuarioAnterior


class Command(BaseCommand):
    help = 'Importa pacientes desde una hoja "pacientes" en un archivo Excel.'

    def add_arguments(self, parser):
        parser.add_argument('excel_path', type=str, help='Ruta del archivo Excel que contiene la hoja "pacientes".')

    def limpiar_rut(self, valor):
        """
        Limpia y normaliza el RUT, especialmente si viene como float o con caracteres invisibles.
        """
        if pd.isna(valor):
            return ''
        if isinstance(valor, float):
            valor = int(valor)  # Convertimos float como 10027549.0 a 10027549
        rut = str(valor).strip()
        rut = rut.replace('\xa0', '').replace('\u200b', '').replace(' ', '')
        return rut

    def es_rut_recien_nacido(self, rut):
        """
        Detecta si el RUT es de recién nacido (90 millones hacia arriba).
        Ejemplo: 91253623-1 -> True
        """
        if not rut:
            return False

        # Extraer solo los números del RUT (antes del guión)
        rut_limpio = rut.split('-')[0] if '-' in rut else rut
        rut_limpio = re.sub(r'[^\d]', '', rut_limpio)

        if not rut_limpio:
            return False

        try:
            rut_numero = int(rut_limpio)
            # Si el RUT es 90 millones o más, es recién nacido
            return rut_numero >= 90000000
        except (ValueError, TypeError):
            return False

    def limpiar_texto(self, texto):
        """
        Limpia texto eliminando caracteres especiales, números y normalizando.
        """
        if pd.isna(texto) or texto is None:
            return ''

        texto = str(texto).strip()

        # Eliminar caracteres especiales, números y símbolos, manteniendo letras, espacios y ñ/Ñ
        texto_limpio = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]', '', texto)

        # Eliminar espacios múltiples
        texto_limpio = re.sub(r'\s+', ' ', texto_limpio)

        return texto_limpio.upper()

    def limpiar_telefono(self, telefono):
        """
        Limpia número de teléfono, manteniendo solo dígitos.
        """
        if pd.isna(telefono) or telefono is None:
            return ''

        telefono = str(telefono).strip()
        # Mantener solo dígitos
        telefono_limpio = re.sub(r'[^\d]', '', telefono)
        return telefono_limpio

    def handle(self, *args, **options):
        excel_path = options['excel_path']

        try:
            # Leer el archivo Excel
            self.stdout.write(self.style.SUCCESS(f'📖 Leyendo archivo Excel: {excel_path}'))
            df = pd.read_excel(excel_path, sheet_name='pacientes', dtype=str)
            total_filas = len(df)
            self.stdout.write(self.style.SUCCESS(f'📊 Total de registros encontrados: {total_filas:,}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Error al leer el archivo: {e}'))
            return

        df.columns = df.columns.str.strip()

        total_creados = 0
        total_actualizados = 0
        total_recien_nacidos_omitidos = 0
        total_errores = 0

        # Crear barra de progreso
        with tqdm(total=total_filas, desc="📋 Procesando pacientes", unit="registro") as pbar:
            for index, row in df.iterrows():
                try:
                    # Limpiar y procesar RUT
                    rut_raw = row.get('rut', '')
                    rut = self.limpiar_rut(rut_raw)

                    # Verificar si es RUT de recién nacido (90 millones o más)
                    if self.es_rut_recien_nacido(rut):
                        total_recien_nacidos_omitidos += 1
                        pbar.update(1)
                        continue

                    # Limpiar campos de texto
                    nombre = self.limpiar_texto(row.get('nombre', ''))
                    apellido_paterno = self.limpiar_texto(row.get('apellido_paterno', ''))
                    apellido_materno = self.limpiar_texto(row.get('apellido_materno', ''))
                    direccion = str(row.get('direccion', '')).strip().upper() if pd.notna(row.get('direccion')) else ''

                    # Limpiar teléfonos
                    numero_telefono1 = self.limpiar_telefono(row.get('numero_telefono1', ''))
                    numero_telefono2 = self.limpiar_telefono(row.get('numero_telefono2', ''))

                    sexo = str(row.get('sexo', '')).strip().upper() if pd.notna(row.get('sexo')) else ''
                    estado_civil = str(row.get('estado_civil', '')).strip().upper() if pd.notna(
                        row.get('estado_civil')) else ''

                    # Fechas
                    fecha_nacimiento_raw = row.get('fecha_nacimiento')
                    fecha_nacimiento = pd.to_datetime(fecha_nacimiento_raw, errors='coerce')
                    fecha_nacimiento = fecha_nacimiento.date() if pd.notna(fecha_nacimiento) else None

                    # IDs relacionados
                    comuna_id = row.get('comuna_id')
                    prevision_id = row.get('prevision_id')
                    genero = str(row.get('genero', '')).strip().upper() if pd.notna(
                        row.get('genero')) else 'NO INFORMADO'

                    # Limpieza del RUT del usuario anterior
                    usuario_anterior_rut_raw = row.get('usuario_anterior_id', '')
                    usuario_anterior_rut = self.limpiar_rut(usuario_anterior_rut_raw)
                    usuario_anterior = None
                    if usuario_anterior_rut:
                        usuario_anterior = UsuarioAnterior.objects.filter(rut=usuario_anterior_rut).first()
                        if not usuario_anterior:
                            self.stdout.write(self.style.WARNING(
                                f"⚠️ UsuarioAnterior con RUT '{usuario_anterior_rut}' no encontrado (Fila {index + 2})"
                            ))

                    # Limpiar campos opcionales de texto
                    rut_madre = self.limpiar_rut(row.get('rut_madre', ''))
                    nombre_social = self.limpiar_texto(row.get('nombre_social', ''))
                    pasaporte = str(row.get('pasaporte', '')).strip().upper() if pd.notna(row.get('pasaporte')) else ''
                    nombres_padre = self.limpiar_texto(row.get('nombres_padre', ''))
                    nombres_madre = self.limpiar_texto(row.get('nombres_madre', ''))
                    nombre_pareja = self.limpiar_texto(row.get('nombre_pareja', ''))
                    representante_legal = self.limpiar_texto(row.get('representante_legal', ''))
                    ocupacion = self.limpiar_texto(row.get('ocupacion', ''))
                    rut_responsable_temporal = self.limpiar_rut(row.get('rut_responsable_temporal', ''))

                    # Booleanos (manejar valores vacíos como False)
                    sin_telefono_val = row.get('sin_telefono', '0')
                    sin_telefono = bool(int(sin_telefono_val)) if sin_telefono_val and sin_telefono_val != '' else False

                    recien_nacido_val = row.get('recien_nacido', '0')
                    recien_nacido = bool(
                        int(recien_nacido_val)) if recien_nacido_val and recien_nacido_val != '' else False

                    extranjero_val = row.get('extranjero', '0')
                    extranjero = bool(int(extranjero_val)) if extranjero_val and extranjero_val != '' else False

                    fallecido_val = row.get('fallecido', '0')
                    fallecido = bool(int(fallecido_val)) if fallecido_val and fallecido_val != '' else False

                    usar_rut_madre_val = row.get('usar_rut_madre_como_responsable', '0')
                    usar_rut_madre_como_responsable = bool(
                        int(usar_rut_madre_val)) if usar_rut_madre_val and usar_rut_madre_val != '' else False

                    # Fecha fallecimiento
                    fecha_fallecimiento_raw = row.get('fecha_fallecimiento')
                    fecha_fallecimiento = pd.to_datetime(fecha_fallecimiento_raw, errors='coerce')
                    fecha_fallecimiento = fecha_fallecimiento.date() if pd.notna(fecha_fallecimiento) else None

                    # Validación de obligatorios
                    if not all([rut, nombre, sexo, estado_civil, comuna_id]):
                        self.stdout.write(
                            self.style.WARNING(f'⚠️ Fila {index + 2}: Faltan datos obligatorios. Se omite.'))
                        total_errores += 1
                        pbar.update(1)
                        continue

                    # Convertir comuna_id y validar
                    try:
                        comuna_id_int = int(float(comuna_id)) if comuna_id and comuna_id != '' else None
                        comuna = Comuna.objects.filter(id=comuna_id_int).first() if comuna_id_int else None
                    except (ValueError, TypeError):
                        comuna = None

                    if not comuna:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️ Fila {index + 2}: Comuna ID {comuna_id} no encontrada.'))
                        total_errores += 1
                        pbar.update(1)
                        continue

                    # Convertir prevision_id
                    try:
                        prevision_id_int = int(float(prevision_id)) if prevision_id and prevision_id != '' else None
                        prevision = Prevision.objects.filter(id=prevision_id_int).first() if prevision_id_int else None
                    except (ValueError, TypeError):
                        prevision = None

                    # Preparar datos para el paciente
                    datos_paciente = {
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
                        'usar_rut_madre_como_responsable': usar_rut_madre_como_responsable
                    }

                    # Crear o actualizar el paciente
                    paciente, created = Paciente.objects.update_or_create(
                        rut=rut,
                        defaults=datos_paciente
                    )

                    if created:
                        total_creados += 1
                    else:
                        total_actualizados += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Error en fila {index + 2}: {e}'))
                    total_errores += 1

                # Actualizar barra de progreso
                pbar.update(1)
                pbar.set_postfix({
                    'Creados': total_creados,
                    'Actualizados': total_actualizados,
                    'RN Omitidos': total_recien_nacidos_omitidos,
                    'Errores': total_errores
                })

        # Resumen final
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN FINAL DE IMPORTACIÓN'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'✅ Pacientes creados: {total_creados:,}'))
        self.stdout.write(self.style.SUCCESS(f'🔄 Pacientes actualizados: {total_actualizados:,}'))
        self.stdout.write(self.style.WARNING(f'👶 Recién nacidos omitidos: {total_recien_nacidos_omitidos:,}'))
        self.stdout.write(self.style.ERROR(f'❌ Errores: {total_errores:,}'))
        self.stdout.write(self.style.SUCCESS(f'📈 Total procesados: {total_creados + total_actualizados:,}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
