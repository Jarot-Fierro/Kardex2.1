import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from tqdm import tqdm

from clinica.models import Ficha
from establecimientos.models.establecimiento import Establecimiento
from establecimientos.models.sectores import Sector
from geografia.models.comuna import Comuna
from personas.models.genero import Genero
from personas.models.pacientes import Paciente
from personas.models.prevision import Prevision


def format_rut(rut):
    """Formatea un RUT con puntos y guion: 20.930.055-9"""
    if not rut:
        return ''

    # Limpiar el RUT de puntos y guiones existentes
    rut = rut.replace('.', '').replace('-', '').strip().upper()

    if not rut:
        return ''

    # Separar número y dígito verificador
    if len(rut) == 1:
        return rut

    # El último carácter es el dígito verificador
    cuerpo = rut[:-1]
    dv = rut[-1]

    # Agregar puntos cada 3 dígitos desde el final
    cuerpo_formateado = ''
    for i, digito in enumerate(cuerpo[::-1]):
        if i > 0 and i % 3 == 0:
            cuerpo_formateado = '.' + cuerpo_formateado
        cuerpo_formateado = digito + cuerpo_formateado

    # Devolver RUT formateado
    return f"{cuerpo_formateado}-{dv}"


def normalize_rut(value):
    """Normaliza el RUT eliminando espacios y convirtiendo a mayúsculas"""
    if pd.isna(value) or value is None:
        return ''
    rut = str(value).strip().upper()
    # Eliminar espacios en blanco
    rut = rut.replace(' ', '')
    return rut


def safe_str(value, default=''):
    """Convierte valores a string de manera segura"""
    if pd.isna(value) or value is None:
        return default
    return str(value).strip()


def normalize_extranjero(value):
    """Normaliza valores para extranjero (CHILENA = False)"""
    if pd.isna(value) or value is None:
        return False
    val = str(value).strip().upper()
    if val in ['SI', 'SÍ', 'YES', 'TRUE', 'VERDADERO', '1', 'EXTRANJERO']:
        return True
    elif val == 'CHILENA':
        return False
    return False


def normalize_fallecido(value):
    """Normaliza valores para fallecido"""
    if pd.isna(value) or value is None:
        return False
    val = str(value).strip().upper()
    if val in ['SI', 'SÍ', 'YES', 'TRUE', 'VERDADERO', '1']:
        return True
    return False


def normalize_pueblo_indigena(value):
    """Normaliza valores para pueblo indígena"""
    if pd.isna(value) or value is None:
        return False
    val = str(value).strip().upper()
    if val in ['SI', 'SÍ', 'YES', 'TRUE', 'VERDADERO', '1']:
        return True
    elif val in ['NO', 'NO SABE']:
        return False
    return False


def get_genero_id(value):
    """Obtiene el ID del género basado en el texto"""
    if pd.isna(value) or value is None:
        return None

    value = str(value).strip().upper()

    # Buscar en la base de datos
    try:
        # Primero por nombre exacto
        genero = Genero.objects.filter(nombre=value).first()
        if not genero:
            # Buscar que contenga el texto
            genero = Genero.objects.filter(nombre__icontains=value).first()

        if genero:
            return genero.id
    except Exception as e:
        print(f"Error buscando género '{value}': {str(e)}")

    # Si no se encuentra, devolver None
    return None


def get_sexo_from_genero(genero_value):
    """Determina el sexo basado en el género"""
    if pd.isna(genero_value) or genero_value is None:
        return 'NO INFORMADO'

    value = str(genero_value).strip().upper()

    if value == 'MASCULINO':
        return 'MASCULINO'
    elif value in ['FEMENINO', 'FEMENINA']:
        return 'FEMENINO'
    else:
        return 'NO INFORMADO'


def get_prevision_id(value):
    """Obtiene el ID de la previsión basado en el texto"""
    if pd.isna(value) or value is None:
        return 1  # Default a Fonasa A

    value = str(value).strip().upper()

    # Buscar en la base de datos
    try:
        # Primero intentar coincidencia exacta
        prevision = Prevision.objects.filter(nombre=value).first()
        if not prevision:
            # Buscar que contenga el texto
            prevision = Prevision.objects.filter(nombre__icontains=value).first()

        if prevision:
            return prevision.id
    except Exception as e:
        print(f"Error buscando previsión '{value}': {str(e)}")

    return 1  # Default a Fonasa A


def get_comuna_id(value):
    """Obtiene el ID de la comuna basado en el nombre"""
    if pd.isna(value) or value is None:
        return 1  # Default

    comuna_nombre = str(value).strip()

    # Primero buscar exacto
    comuna = Comuna.objects.filter(nombre=comuna_nombre).first()

    # Si no existe, buscar que contenga el texto
    if not comuna:
        comuna = Comuna.objects.filter(nombre__icontains=comuna_nombre).first()

    return comuna.id if comuna else 1


def get_sector_id(value, establecimiento_id=None):
    """Obtiene el ID del sector basado en el nombre del color"""
    if pd.isna(value) or value is None:
        return None

    color_nombre = str(value).strip().upper()

    # Buscar el sector por el nombre del color
    try:
        # Si tenemos establecimiento_id, filtramos por él
        if establecimiento_id:
            sector = Sector.objects.filter(
                establecimiento_id=establecimiento_id,
                color__nombre__iexact=color_nombre
            ).first()
        else:
            sector = Sector.objects.filter(color__nombre__iexact=color_nombre).first()

        # Si no se encuentra exacto, buscar que contenga
        if not sector and establecimiento_id:
            sector = Sector.objects.filter(
                establecimiento_id=establecimiento_id,
                color__nombre__icontains=color_nombre
            ).first()
        elif not sector:
            sector = Sector.objects.filter(color__nombre__icontains=color_nombre).first()

        if sector:
            return sector.id
    except Exception as e:
        print(f"Error buscando sector con color '{color_nombre}': {str(e)}")

    return None


class Command(BaseCommand):
    help = 'Importa fichas desde Excel con creación automática de pacientes'

    def add_arguments(self, parser):
        parser.add_argument('ruta_excel', type=str, help='Ruta del archivo Excel a importar')
        parser.add_argument('--establecimiento', type=int, default=4,
                            help='ID del establecimiento (default: 4 para Contulmo)')
        parser.add_argument('--hoja', type=str, default='pacientes',
                            help='Nombre de la hoja del Excel (default: pacientes)')
        parser.add_argument('--debug', action='store_true', help='Activar modo debug para ver más detalles')

    def handle(self, *args, **options):
        ruta = options['ruta_excel']
        establecimiento_id = options['establecimiento']
        hoja_nombre = options['hoja']
        debug_mode = options['debug']
        log_lines = []

        self.stdout.write(f'\n📖 Leyendo Excel: {ruta}')
        self.stdout.write(f'🏥 Establecimiento ID: {establecimiento_id}')
        self.stdout.write(f'📄 Hoja: {hoja_nombre}')
        if debug_mode:
            self.stdout.write('🔍 Modo debug activado')

        # Leer el Excel
        try:
            df = pd.read_excel(
                ruta,
                sheet_name=hoja_nombre,
                dtype=str,
                engine='openpyxl'
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Error al leer el Excel: {str(e)}'))
            return

        # Mostrar las primeras filas para debug
        if debug_mode:
            self.stdout.write(f'\n📊 Primeras 5 filas del DataFrame:')
            self.stdout.write(str(df.head()))
            self.stdout.write(f'\n📊 Columnas disponibles: {list(df.columns)}')

        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip().str.lower()

        # Mostrar columnas normalizadas
        if debug_mode:
            self.stdout.write(f'📊 Columnas normalizadas: {list(df.columns)}')

        # Columnas requeridas
        columnas_requeridas = {
            'rut',
            'nombre',
            'apellido_paterno',
            'apellido_materno',
            'numero_ficha'
        }

        # Verificar columnas requeridas
        faltantes = columnas_requeridas - set(df.columns)
        if faltantes:
            self.stderr.write(self.style.ERROR(
                f'❌ Columnas faltantes en Excel: {faltantes}'
            ))
            self.stdout.write(f'Columnas disponibles: {list(df.columns)}')
            return

        # Obtener establecimiento
        try:
            establecimiento = Establecimiento.objects.get(id=establecimiento_id)
            self.stdout.write(f'✅ Establecimiento: {establecimiento.nombre}')
        except Establecimiento.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'❌ Establecimiento con ID {establecimiento_id} no existe'))
            return

        # Cache de datos
        pacientes_cache = {}
        for p in Paciente.objects.all():
            rut_norm = normalize_rut(p.rut)
            if rut_norm:
                pacientes_cache[rut_norm] = p

        fichas_existentes = set(
            Ficha.objects.filter(establecimiento=establecimiento)
            .values_list('numero_ficha_sistema', flat=True)
        )

        total_filas = len(df)
        creadas = 0
        omitidas = 0
        duplicadas = 0
        pacientes_creados = 0
        pacientes_modificados = 0
        fichas_modificadas = 0
        error_formato = 0

        # =========================
        # IMPORTACIÓN
        # =========================
        with transaction.atomic():
            for idx, row in tqdm(
                    df.iterrows(),
                    total=total_filas,
                    desc='⏳ Importando fichas',
                    unit='fila'
            ):
                fila_excel = idx + 2  # Considerando encabezado

                # Obtener datos básicos
                rut_limpio = normalize_rut(row.get('rut'))
                nombre = safe_str(row.get('nombre'))
                apellido_paterno = safe_str(row.get('apellido_paterno'))
                apellido_materno = safe_str(row.get('apellido_materno'))
                numero_ficha_raw = safe_str(row.get('numero_ficha'))

                # Debug: mostrar datos de la primera fila
                if debug_mode and idx == 0:
                    self.stdout.write(f'\n🔍 DEBUG - Primera fila:')
                    self.stdout.write(f'  RUT limpio: "{rut_limpio}"')
                    self.stdout.write(f'  Nombre: "{nombre}"')
                    self.stdout.write(f'  Apellido Paterno: "{apellido_paterno}"')
                    self.stdout.write(f'  Apellido Materno: "{apellido_materno}"')
                    self.stdout.write(f'  Número Ficha: "{numero_ficha_raw}"')
                    self.stdout.write(f'  Tipo RUT: {type(row.get("rut"))}')
                    self.stdout.write(f'  Valor crudo RUT: {row.get("rut")}')

                # Validación básica
                if not rut_limpio:
                    omitidas += 1
                    error_formato += 1
                    log_lines.append(
                        f'FILA {fila_excel} | RUT VACÍO | NOMBRE={nombre}'
                    )
                    if debug_mode:
                        self.stdout.write(f'  ❌ RUT vacío en fila {fila_excel}')
                    continue

                if not nombre:
                    omitidas += 1
                    error_formato += 1
                    log_lines.append(
                        f'FILA {fila_excel} | NOMBRE VACÍO | RUT={rut_limpio}'
                    )
                    if debug_mode:
                        self.stdout.write(f'  ❌ Nombre vacío en fila {fila_excel}')
                    continue

                if not apellido_paterno:
                    omitidas += 1
                    error_formato += 1
                    log_lines.append(
                        f'FILA {fila_excel} | APELLIDO PATERNO VACÍO | RUT={rut_limpio}'
                    )
                    if debug_mode:
                        self.stdout.write(f'  ❌ Apellido paterno vacío en fila {fila_excel}')
                    continue

                if not apellido_materno:
                    omitidas += 1
                    error_formato += 1
                    log_lines.append(
                        f'FILA {fila_excel} | APELLIDO MATERNO VACÍO | RUT={rut_limpio}'
                    )
                    if debug_mode:
                        self.stdout.write(f'  ❌ Apellido materno vacío en fila {fila_excel}')
                    continue

                # Validar número de ficha
                try:
                    numero_ficha = int(float(numero_ficha_raw)) if numero_ficha_raw else 0
                    if numero_ficha <= 0:
                        raise ValueError("Número de ficha inválido")
                except (ValueError, TypeError) as e:
                    omitidas += 1
                    error_formato += 1
                    log_lines.append(
                        f'FILA {fila_excel} | NÚMERO FICHA INVÁLIDO | RUT={rut_limpio} | FICHA={numero_ficha_raw} | ERROR={str(e)}'
                    )
                    if debug_mode:
                        self.stdout.write(f'  ❌ Número ficha inválido en fila {fila_excel}: {numero_ficha_raw}')
                    continue

                # Verificar si la ficha ya existe
                if numero_ficha in fichas_existentes:
                    omitidas += 1
                    duplicadas += 1
                    log_lines.append(
                        f'FILA {fila_excel} | FICHA DUPLICADA | RUT={rut_limpio} | FICHA={numero_ficha}'
                    )
                    if debug_mode:
                        self.stdout.write(f'  ⚠️ Ficha duplicada en fila {fila_excel}: {numero_ficha}')
                    continue

                # Buscar o crear/actualizar paciente
                paciente = pacientes_cache.get(rut_limpio)
                paciente_fue_modificado = False

                if not paciente:
                    # Crear nuevo paciente
                    try:
                        # Obtener valores para el paciente
                        extranjero_val = normalize_extranjero(row.get('extranjero'))
                        fallecido_val = normalize_fallecido(row.get('fallecido'))
                        pueblo_indigena_val = normalize_pueblo_indigena(row.get('pueblo_indigena'))
                        comuna_id_val = get_comuna_id(row.get('comuna_id'))
                        prevision_id_val = get_prevision_id(row.get('prevision'))
                        genero_id_val = get_genero_id(row.get('genero'))
                        sexo_val = get_sexo_from_genero(row.get('genero'))

                        if debug_mode and idx < 3:
                            self.stdout.write(f'\n🔍 DEBUG - Valores para paciente:')
                            self.stdout.write(f'  Extranjero: {extranjero_val}')
                            self.stdout.write(f'  Fallecido: {fallecido_val}')
                            self.stdout.write(f'  Pueblo indígena: {pueblo_indigena_val}')
                            self.stdout.write(f'  Comuna ID: {comuna_id_val}')
                            self.stdout.write(f'  Previsión ID: {prevision_id_val}')
                            self.stdout.write(f'  Género ID: {genero_id_val}')
                            self.stdout.write(f'  Sexo: {sexo_val}')

                        # Formatear el RUT con puntos y guion
                        rut_formateado = format_rut(rut_limpio)

                        if debug_mode and idx < 3:
                            self.stdout.write(f'  RUT formateado: "{rut_formateado}"')

                        paciente = Paciente(
                            rut=rut_formateado,  # Usar RUT formateado
                            nombre=nombre,
                            apellido_paterno=apellido_paterno,
                            apellido_materno=apellido_materno,
                            extranjero=extranjero_val,
                            fallecido=fallecido_val,
                            pueblo_indigena=pueblo_indigena_val,
                            comuna_id=comuna_id_val,
                            prevision_id=prevision_id_val,
                            genero_id=genero_id_val,
                            sexo=sexo_val,
                            estado_civil='NO INFORMADO'
                        )

                        # Guardar paciente (esto generará automáticamente el código)
                        paciente.save()
                        pacientes_creados += 1

                        # Actualizar cache con RUT limpio
                        pacientes_cache[rut_limpio] = paciente

                        log_lines.append(
                            f'FILA {fila_excel} | PACIENTE CREADO | RUT={rut_formateado} | ID={paciente.id}'
                        )

                        if debug_mode:
                            self.stdout.write(f'  ✅ Paciente creado: {rut_formateado} - ID: {paciente.id}')

                    except Exception as e:
                        omitidas += 1
                        error_formato += 1
                        log_lines.append(
                            f'FILA {fila_excel} | ERROR CREANDO PACIENTE | RUT={rut_limpio} | ERROR={str(e)}'
                        )
                        if debug_mode:
                            self.stdout.write(f'  ❌ Error creando paciente: {str(e)}')
                        continue
                else:
                    # Verificar si el paciente necesita actualización (formato del RUT)
                    rut_formateado = format_rut(rut_limpio)

                    # Obtener valores para actualización
                    extranjero_val = normalize_extranjero(row.get('extranjero'))
                    fallecido_val = normalize_fallecido(row.get('fallecido'))
                    pueblo_indigena_val = normalize_pueblo_indigena(row.get('pueblo_indigena'))
                    comuna_id_val = get_comuna_id(row.get('comuna_id'))
                    prevision_id_val = get_prevision_id(row.get('prevision'))
                    genero_id_val = get_genero_id(row.get('genero'))
                    sexo_val = get_sexo_from_genero(row.get('genero'))

                    # Verificar si hay cambios
                    cambios = []

                    # Verificar formato del RUT
                    if paciente.rut != rut_formateado:
                        paciente.rut = rut_formateado
                        cambios.append(f'RUT: {paciente.rut} -> {rut_formateado}')
                        paciente_fue_modificado = True

                    # Verificar otros campos básicos
                    if paciente.nombre != nombre:
                        paciente.nombre = nombre
                        cambios.append(f'Nombre: {paciente.nombre} -> {nombre}')
                        paciente_fue_modificado = True

                    if paciente.apellido_paterno != apellido_paterno:
                        paciente.apellido_paterno = apellido_paterno
                        cambios.append(f'Apellido paterno: {paciente.apellido_paterno} -> {apellido_paterno}')
                        paciente_fue_modificado = True

                    if paciente.apellido_materno != apellido_materno:
                        paciente.apellido_materno = apellido_materno
                        cambios.append(f'Apellido materno: {paciente.apellido_materno} -> {apellido_materno}')
                        paciente_fue_modificado = True

                    # Verificar campos booleanos y ForeignKeys
                    if paciente.extranjero != extranjero_val:
                        paciente.extranjero = extranjero_val
                        cambios.append(f'Extranjero: {paciente.extranjero} -> {extranjero_val}')
                        paciente_fue_modificado = True

                    if paciente.fallecido != fallecido_val:
                        paciente.fallecido = fallecido_val
                        cambios.append(f'Fallecido: {paciente.fallecido} -> {fallecido_val}')
                        paciente_fue_modificado = True

                    if paciente.pueblo_indigena != pueblo_indigena_val:
                        paciente.pueblo_indigena = pueblo_indigena_val
                        cambios.append(f'Pueblo indígena: {paciente.pueblo_indigena} -> {pueblo_indigena_val}')
                        paciente_fue_modificado = True

                    if paciente.comuna_id != comuna_id_val:
                        paciente.comuna_id = comuna_id_val
                        cambios.append(f'Comuna ID: {paciente.comuna_id} -> {comuna_id_val}')
                        paciente_fue_modificado = True

                    if paciente.prevision_id != prevision_id_val:
                        paciente.prevision_id = prevision_id_val
                        cambios.append(f'Previsión ID: {paciente.prevision_id} -> {prevision_id_val}')
                        paciente_fue_modificado = True

                    if paciente.genero_id != genero_id_val:
                        paciente.genero_id = genero_id_val
                        cambios.append(f'Género ID: {paciente.genero_id} -> {genero_id_val}')
                        paciente_fue_modificado = True

                    if paciente.sexo != sexo_val:
                        paciente.sexo = sexo_val
                        cambios.append(f'Sexo: {paciente.sexo} -> {sexo_val}')
                        paciente_fue_modificado = True

                    # Si hay cambios, guardar
                    if paciente_fue_modificado:
                        try:
                            paciente.save()
                            pacientes_modificados += 1

                            log_lines.append(
                                f'FILA {fila_excel} | PACIENTE ACTUALIZADO | RUT={rut_formateado} | ID={paciente.id} | CAMBIOS: {", ".join(cambios)}'
                            )

                            if debug_mode and idx < 3:
                                self.stdout.write(f'  🔄 Paciente actualizado: {rut_formateado} - ID: {paciente.id}')
                                self.stdout.write(f'  Cambios: {", ".join(cambios)}')

                        except Exception as e:
                            omitidas += 1
                            error_formato += 1
                            log_lines.append(
                                f'FILA {fila_excel} | ERROR ACTUALIZANDO PACIENTE | RUT={rut_limpio} | ERROR={str(e)}'
                            )
                            if debug_mode:
                                self.stdout.write(f'  ❌ Error actualizando paciente: {str(e)}')
                            continue

                # Crear la ficha
                try:
                    sector_id_val = get_sector_id(row.get('sector'), establecimiento_id)

                    if debug_mode and idx < 3:
                        self.stdout.write(f'🔍 DEBUG - Buscando sector: "{row.get("sector")}" -> ID: {sector_id_val}')

                    # Verificar si ya existe una ficha para este paciente en este establecimiento
                    ficha_existente = Ficha.objects.filter(
                        paciente=paciente,
                        establecimiento=establecimiento,
                        numero_ficha_sistema=numero_ficha
                    ).first()

                    if ficha_existente:
                        # Actualizar ficha existente
                        ficha_actualizada = False

                        if ficha_existente.sector_id != sector_id_val:
                            ficha_existente.sector_id = sector_id_val
                            ficha_actualizada = True

                        observacion_nueva = f'Importado desde Excel - Fila {fila_excel}'
                        if ficha_existente.observacion != observacion_nueva:
                            ficha_existente.observacion = observacion_nueva
                            ficha_actualizada = True

                        if ficha_actualizada:
                            ficha_existente.save()
                            fichas_modificadas += 1

                            log_lines.append(
                                f'FILA {fila_excel} | FICHA ACTUALIZADA | RUT={rut_limpio} | FICHA={numero_ficha} | ID={ficha_existente.id}'
                            )

                            if debug_mode and idx < 3:
                                self.stdout.write(f'  🔄 Ficha actualizada: {numero_ficha}')
                    else:
                        # Crear nueva ficha
                        ficha = Ficha.objects.create(
                            numero_ficha_sistema=numero_ficha,
                            paciente=paciente,
                            establecimiento=establecimiento,
                            sector_id=sector_id_val,
                            observacion=f'Importado desde Excel - Fila {fila_excel}',
                            fecha_mov=None,  # No hay fecha en el Excel proporcionado
                            usuario=None
                        )

                        fichas_existentes.add(numero_ficha)
                        creadas += 1

                        log_lines.append(
                            f'FILA {fila_excel} | FICHA CREADA | RUT={rut_limpio} | FICHA={numero_ficha} | ID={ficha.id}'
                        )

                        if debug_mode and idx < 3:
                            self.stdout.write(f'  ✅ Ficha creada: {numero_ficha}')

                except Exception as e:
                    omitidas += 1
                    error_formato += 1
                    log_lines.append(
                        f'FILA {fila_excel} | ERROR CREANDO/ACTUALIZANDO FICHA | RUT={rut_limpio} | ERROR={str(e)}'
                    )
                    if debug_mode:
                        self.stdout.write(f'  ❌ Error creando/actualizando ficha: {str(e)}')
                    continue

        # Guardar log
        with open('log_importacion_fichas_excel.txt', 'w', encoding='utf-8') as f:
            f.write('=' * 60 + '\n')
            f.write('LOG DE IMPORTACIÓN DE FICHAS DESDE EXCEL\n')
            f.write('=' * 60 + '\n\n')
            f.write('\n'.join(log_lines))

        # =========================
        # RESUMEN
        # =========================
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN IMPORTACIÓN'))
        self.stdout.write(self.style.SUCCESS(f'📄 Total filas en Excel: {total_filas}'))
        self.stdout.write(self.style.SUCCESS(f'✅ Fichas creadas: {creadas}'))
        self.stdout.write(self.style.SUCCESS(f'🔄 Fichas actualizadas: {fichas_modificadas}'))
        self.stdout.write(self.style.SUCCESS(f'👤 Pacientes creados: {pacientes_creados}'))
        self.stdout.write(self.style.SUCCESS(f'🔄 Pacientes actualizados: {pacientes_modificados}'))
        self.stdout.write(self.style.WARNING(f'⚠️ Omitidas: {omitidas}'))
        self.stdout.write(self.style.WARNING(f'🔁 Duplicadas: {duplicadas}'))
        self.stdout.write(self.style.ERROR(f'❌ Error formato: {error_formato}'))

        # Mostrar primeros errores del log
        if error_formato > 0 and len(log_lines) > 0:
            self.stdout.write('\n🔍 Primeros 5 errores:')
            for i, line in enumerate(log_lines[:5]):
                self.stdout.write(f'  {line}')

        self.stdout.write(self.style.SUCCESS('📄 Log generado: log_importacion_fichas_excel.txt'))
        self.stdout.write('=' * 60)
