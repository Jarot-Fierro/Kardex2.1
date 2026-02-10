# python manage.py importar_pacientes "C:\Users\jarot\Desktop\Exportacion\paciente.xlsx"

import warnings
from datetime import datetime

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from tqdm import tqdm

from geografia.models.comuna import Comuna
from personas.models.pacientes import Paciente
from personas.models.prevision import Prevision
from personas.models.usuario_anterior import UsuarioAnterior


class Command(BaseCommand):
    help = 'Importa pacientes desde Excel (incluye RN + captura líneas malas).'

    def add_arguments(self, parser):
        parser.add_argument('excel_path', type=str, help='Ruta del archivo Excel (.xlsx, .xls).')
        parser.add_argument('--sheet', type=str, default=0, help='Nombre o índice de la hoja (por defecto: 0)')
        parser.add_argument('--skiprows', type=int, default=0, help='Filas a saltar al inicio')

    # ================== LIMPIEZAS ==================

    def limpiar_bool(self, valor):
        if pd.isna(valor) or valor in ('', None):
            return False
        valor_str = str(valor).strip().lower()
        if valor_str in ('1', 'true', 't', 'yes', 'y', 'si', 'sí'):
            return True
        elif valor_str in ('0', 'false', 'f', 'no', 'n'):
            return False
        return False

    def limpiar_entero(self, valor):
        if pd.isna(valor) or valor in ('', None, 'None', 'nan', 'NAN', '0', 0):
            return None
        try:
            # Para Excel, a veces viene como float
            if isinstance(valor, float):
                if valor.is_integer():
                    return int(valor)
                else:
                    return None
            valor_limpio = str(valor).strip().replace('.0', '')
            if not valor_limpio or valor_limpio in ('None', 'nan', '0'):
                return None
            return int(valor_limpio)
        except Exception:
            return None

    def limpiar_texto(self, valor):
        if pd.isna(valor) or valor in ('', None, 'None', 'nan', 'NAN'):
            return None
        texto = str(valor).strip()
        if texto.startswith('\ufeff'):
            texto = texto[1:]
        if texto in ('None', 'nan', 'NAN'):
            return None
        return texto

    def limpiar_fecha(self, valor):
        if pd.isna(valor) or valor in ('', None):
            return None

        # Si ya es datetime de pandas
        if isinstance(valor, pd.Timestamp):
            if valor == pd.Timestamp('1900-01-01'):
                return None
            # Convertir a datetime con timezone
            try:
                return timezone.make_aware(valor.to_pydatetime())
            except Exception:
                return valor.to_pydatetime()

        valor_str = str(valor).strip()

        if not valor_str or valor_str in ('01-01-1900', '1900-01-01', '1900-01-01 00:00:00', '01-01-1900 00:00:00'):
            return None

        # Limpiar formato de fecha de Excel (a veces viene como número de serie)
        try:
            # Intentar parsear como fecha de Excel (número de serie)
            fecha_num = float(valor_str)
            fecha = pd.Timestamp('1899-12-30') + pd.Timedelta(days=fecha_num)
            if fecha == pd.Timestamp('1900-01-01'):
                return None
            return fecha.to_pydatetime()
        except (ValueError, TypeError):
            pass

        formatos = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d-%m-%Y %H:%M:%S',
            '%d-%m-%Y',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y'
        ]

        for formato in formatos:
            try:
                # Parsear como datetime
                fecha_dt = datetime.strptime(valor_str, formato)
                if fecha_dt.year == 1900 and fecha_dt.month == 1 and fecha_dt.day == 1:
                    return None
                return fecha_dt
            except Exception:
                continue

        return None

    def limpiar_sexo(self, valor):
        if pd.isna(valor) or valor in ('', None):
            return 'NO INFORMADO'
        v = str(valor).strip().upper()
        if v in ('M', 'MASCULINO', 'HOMBRE', 'H'):
            return 'M'
        elif v in ('F', 'FEMENINO', 'MUJER'):
            return 'F'
        return 'NO INFORMADO'

    def limpiar_estado_civil(self, valor):
        if pd.isna(valor) or valor in ('', None):
            return 'NO INFORMADO'
        v = str(valor).strip().upper()
        if v in ('S', 'SOLTERO', 'SOLTERA'):
            return 'S'
        elif v in ('C', 'CASADO', 'CASADA'):
            return 'C'
        elif v in ('V', 'VIUDO', 'VIUDA'):
            return 'V'
        elif v in ('D', 'DIVORCIADO', 'DIVORCIADA'):
            return 'D'
        elif v in ('I', 'INDEFINIDO', 'NO INFORMADO'):
            return 'NO INFORMADO'
        return 'NO INFORMADO'

    # ================== BUSCAR POR CÓDIGO ==================

    def buscar_comuna_por_codigo(self, codigo, comunas_dict):
        if not codigo:
            return None
        try:
            codigo_int = int(codigo)
            return comunas_dict.get(codigo_int)
        except (ValueError, TypeError):
            return None

    def buscar_prevision_por_codigo(self, codigo, previsiones_dict):
        if not codigo:
            return None
        try:
            codigo_int = int(codigo)
            return previsiones_dict.get(codigo_int)
        except (ValueError, TypeError):
            return None

    # ================== MAIN ==================

    def handle(self, *args, **options):
        # Desactivar warnings específicos de Django
        warnings.filterwarnings(
            'ignore',
            message='DateTimeField .* received a naive datetime',
            category=RuntimeWarning
        )

        excel_path = options['excel_path']
        sheet = options['sheet']
        skiprows = options['skiprows']

        self.stdout.write(self.style.SUCCESS(f'Leyendo Excel: {excel_path}'))
        self.stdout.write(self.style.SUCCESS(f'Hoja: "{sheet}" | Saltar filas: {skiprows}'))

        try:
            # Leer el archivo Excel
            df = pd.read_excel(
                excel_path,
                sheet_name=sheet,
                skiprows=skiprows,
                dtype=str,  # Leer all como string para mayor control
                na_values=['', ' ', 'NaN', 'N/A', 'NULL', 'None'],
                keep_default_na=True
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error leyendo Excel: {e}'))
            return

        # Limpiar nombres de columnas
        df.columns = [str(col).strip() for col in df.columns]
        df.columns = [col.replace('\ufeff', '') for col in df.columns]

        # Reemplazar NaN por cadenas vacías para procesamiento consistente
        df = df.fillna('')

        self.stdout.write(self.style.SUCCESS(f'Columnas detectadas: {list(df.columns)}'))
        self.stdout.write(self.style.SUCCESS(f'Total de columnas: {len(df.columns)}'))

        total_leidas = len(df)
        self.stdout.write(self.style.SUCCESS(f'Registros leídos: {total_leidas:,}'))

        # Mostrar primeras filas para verificación
        self.stdout.write(self.style.SUCCESS('\nPrimeras filas para verificación:'))
        for i in range(min(3, len(df))):
            self.stdout.write(f'Fila {i}: {dict(df.iloc[i].head(5))}')

        # ================== PRECARGA ==================

        self.stdout.write(self.style.SUCCESS('\nPrecargando datos...'))

        pacientes_existentes_count = Paciente.objects.count()
        self.stdout.write(self.style.SUCCESS(f'Pacientes existentes en BD: {pacientes_existentes_count:,}'))

        # Verificar RUTs únicos en el Excel para detectar duplicados
        ruts_excel = {}
        duplicados_excel = 0
        for idx, row in df.iterrows():
            # Verificar diferentes posibles nombres de columna para RUT
            rut = None
            for col_name in ['rut', 'cod_rutpac', 'RUT', 'rut_paciente']:
                if col_name in df.columns:
                    rut = self.limpiar_texto(row.get(col_name))
                    if rut:
                        break

            if rut:
                rut = rut.strip().upper()
                if rut in ruts_excel:
                    duplicados_excel += 1
                else:
                    ruts_excel[rut] = idx

        if duplicados_excel > 0:
            self.stdout.write(self.style.WARNING(f'RUTs duplicados en Excel: {duplicados_excel:,}'))

        # Cargar RUTs existentes para evitar duplicados
        ruts_existentes = set(Paciente.objects.values_list('rut', flat=True))
        self.stdout.write(self.style.SUCCESS(f'RUTs existentes en BD: {len(ruts_existentes):,}'))

        # Cargar comunas
        comunas_por_codigo = {}
        for comuna in Comuna.objects.all():
            if comuna.codigo is not None:
                try:
                    codigo_int = int(comuna.codigo)
                    comunas_por_codigo[codigo_int] = comuna
                except (ValueError, TypeError):
                    continue

        self.stdout.write(self.style.SUCCESS(f'Comunas cargadas: {len(comunas_por_codigo):,}'))

        # Cargar previsiones
        previsiones_por_codigo = {}
        for prevision in Prevision.objects.all():
            if prevision.codigo is not None:
                try:
                    codigo_int = int(prevision.codigo)
                    previsiones_por_codigo[codigo_int] = prevision
                except (ValueError, TypeError):
                    continue

        # Mostrar códigos de previsiones disponibles
        codigos_prevision_disponibles = list(previsiones_por_codigo.keys())
        self.stdout.write(self.style.SUCCESS(f'Previsiones cargadas: {len(previsiones_por_codigo):,}'))
        self.stdout.write(self.style.SUCCESS(f'Códigos de previsión disponibles: {codigos_prevision_disponibles}'))

        usuarios_anteriores = {u.rut: u for u in UsuarioAnterior.objects.all()}
        self.stdout.write(self.style.SUCCESS(f'Usuarios anteriores cargados: {len(usuarios_anteriores):,}'))

        # Buscar comuna default (código 206 o la primera disponible)
        COMUNA_DEFAULT = None
        if comunas_por_codigo.get(206):
            COMUNA_DEFAULT = comunas_por_codigo[206]
            self.stdout.write(self.style.SUCCESS(f'Comuna default: {COMUNA_DEFAULT.nombre} (código 206)'))
        else:
            COMUNA_DEFAULT = Comuna.objects.first()
            if COMUNA_DEFAULT:
                self.stdout.write(self.style.WARNING(f'Usando comuna default alternativa: {COMUNA_DEFAULT.nombre}'))

        if not COMUNA_DEFAULT:
            self.stderr.write(self.style.ERROR('No existe comuna default'))
            return

        # ================== MAPEO DE COLUMNAS ==================

        # Función para encontrar el nombre correcto de columna
        def encontrar_columna(nombres_posibles, df):
            for nombre in nombres_posibles:
                if nombre in df.columns:
                    return nombre
            return None

        # Mapear nombres de columnas posibles
        mapeo_columnas = {
            'rut': encontrar_columna(['rut', 'cod_rutpac', 'RUT'], df),
            'id_anterior': encontrar_columna(['id_anterior', 'id', 'ID'], df),
            'nombre': encontrar_columna(['nombre', 'nom_nombre', 'NOMBRE'], df),
            'apellido_paterno': encontrar_columna(['apellido_paterno', 'nom_apepat', 'APELLIDO_PATERNO'], df),
            'apellido_materno': encontrar_columna(['apellido_materno', 'nom_apemat', 'APELLIDO_MATERNO'], df),
            'fecha_nacimiento': encontrar_columna(['fecha_nacimiento', 'fec_nacimi', 'FECHA_NACIMIENTO'], df),
            'sexo': encontrar_columna(['sexo', 'ind_tisexo', 'SEXO'], df),
            'estado_civil': encontrar_columna(['estado_civil', 'ind_estciv', 'ESTADO_CIVIL'], df),
            'direccion': encontrar_columna(['direccion', 'nom_direcc', 'DIRECCION'], df),
            'comuna': encontrar_columna(['comuna', 'cod_comuna', 'COMUNA'], df),
            'prevision': encontrar_columna(['prevision', 'PREVISION'], df),
            'prevision2': encontrar_columna(['prevision2', 'PREVISION2'], df),
            'usuario': encontrar_columna(['usuario', 'usuario_anterior', 'USUARIO'], df),
            'pasaporte': encontrar_columna(['pasaporte', 'PASAPORTE'], df),
            'rut_madre': encontrar_columna(['rut_madre', 'RUT_MADRE'], df),
            'recien_nacido': encontrar_columna(['recien_nacido', 'RECIEN_NACIDO'], df),
            'extranjero': encontrar_columna(['extranjero', 'EXTRANJERO'], df),
            'fallecido': encontrar_columna(['fallecido', 'FALLECIDO'], df),
            'fecha_fallecimiento': encontrar_columna(['fecha_fallecimiento', 'fecha_fallecido', 'FECHA_FALLECIMIENTO'],
                                                     df),
            'nombres_padre': encontrar_columna(['nombres_padre', 'nom_npadre', 'NOMBRES_PADRE'], df),
            'nombres_madre': encontrar_columna(['nombres_madre', 'nom_nmadre', 'NOMBRES_MADRE'], df),
            'nombre_pareja': encontrar_columna(['nombre_pareja', 'nom_pareja', 'NOMBRE_PAREJA'], df),
            'numero_telefono1': encontrar_columna(['numero_telefono1', 'num_telefo1', 'TELEFONO1'], df),
            'numero_telefono2': encontrar_columna(['numero_telefono2', 'num_telefo2', 'TELEFONO2'], df),
            'ocupacion': encontrar_columna(['ocupacion', 'OCUPACION'], df),
            'representante_legal': encontrar_columna(['representante_legal', 'REPRESENTANTE_LEGAL'], df),
            'nombre_social': encontrar_columna(['nombre_social', 'NOMBRE_SOCIAL'], df),
        }

        self.stdout.write(self.style.SUCCESS('\nMapeo de columnas encontradas:'))
        for key, value in mapeo_columnas.items():
            if value:
                self.stdout.write(f'  {key}: {value}')

        # ================== CONTADORES ==================

        creados = 0
        omitidos = 0
        duplicados = 0
        rn_creados = 0
        comuna_default_count = 0
        prevision_no_encontrada = 0
        errores_validacion = 0
        sin_rut = 0

        buffer = []
        BATCH_SIZE = 1000

        # ================== IMPORTACIÓN ==================

        self.stdout.write(self.style.SUCCESS('\nIniciando importación...'))

        with tqdm(total=total_leidas, desc='Importando pacientes', unit='reg') as pbar:
            for index, row in df.iterrows():
                try:
                    # Obtener RUT usando el mapeo de columnas
                    rut = None
                    col_rut = mapeo_columnas['rut']
                    if col_rut:
                        rut = self.limpiar_texto(row.get(col_rut))

                    if not rut:
                        sin_rut += 1
                        pbar.update(1)
                        continue

                    rut = rut.strip().upper()

                    # Verificar si ya existe en BD
                    if rut in ruts_existentes:
                        self.stdout.write(
                            self.style.WARNING(f'Paciente con RUT {rut} ya existe en la base de datos. Omitiendo.'))
                        omitidos += 1
                        pbar.update(1)
                        continue

                    # BUSCAR COMUNA POR CÓDIGO
                    codigo_comuna = None
                    col_comuna = mapeo_columnas['comuna']
                    if col_comuna:
                        codigo_comuna = self.limpiar_entero(row.get(col_comuna))

                    comuna = self.buscar_comuna_por_codigo(codigo_comuna, comunas_por_codigo)

                    if not comuna:
                        comuna = COMUNA_DEFAULT
                        comuna_default_count += 1

                    # BUSCAR PREVISIÓN POR CÓDIGO
                    # Intentar con 'prevision' y luego con 'prevision2'
                    codigo_prevision = None
                    col_prevision = mapeo_columnas['prevision']
                    if col_prevision:
                        codigo_prevision = self.limpiar_entero(row.get(col_prevision))

                    if codigo_prevision is None or codigo_prevision == 0:
                        col_prevision2 = mapeo_columnas['prevision2']
                        if col_prevision2:
                            codigo_prevision = self.limpiar_entero(row.get(col_prevision2))

                    prevision = None
                    if codigo_prevision:
                        prevision = self.buscar_prevision_por_codigo(codigo_prevision, previsiones_por_codigo)

                    if not prevision:
                        prevision_no_encontrada += 1
                        # No asignar previsión si no se encuentra

                    # PROCESAR FECHA DE NACIMIENTO
                    fecha_nacimiento_raw = None
                    col_fecha_nac = mapeo_columnas['fecha_nacimiento']
                    if col_fecha_nac:
                        fecha_nacimiento_raw = row.get(col_fecha_nac)
                    fecha_nacimiento = self.limpiar_fecha(fecha_nacimiento_raw)

                    # BUSCAR USUARIO ANTERIOR POR RUT
                    usuario_rut = None
                    col_usuario = mapeo_columnas['usuario']
                    if col_usuario:
                        usuario_rut = self.limpiar_texto(row.get(col_usuario))
                    usuario_anterior = usuarios_anteriores.get(usuario_rut) if usuario_rut else None

                    # Obtener otros campos usando el mapeo
                    def obtener_valor(campo):
                        col = mapeo_columnas.get(campo)
                        if col and col in row:
                            return self.limpiar_texto(row.get(col))
                        return None

                    # Validar campos requeridos
                    nombre = obtener_valor('nombre') or "NO INFORMADO"
                    apellido_paterno = obtener_valor('apellido_paterno') or "NO INFORMADO"
                    apellido_materno = obtener_valor('apellido_materno') or "NO INFORMADO"

                    # Validar que el RUT no esté vacío
                    if not rut or rut == '':
                        errores_validacion += 1
                        pbar.update(1)
                        continue

                    # CREAR PACIENTE
                    paciente = Paciente(
                        rut=rut,
                        id_anterior=self.limpiar_entero(obtener_valor('id_anterior')),
                        nombre=nombre,
                        apellido_paterno=apellido_paterno,
                        apellido_materno=apellido_materno,
                        rut_madre=obtener_valor('rut_madre'),
                        pasaporte=obtener_valor('pasaporte'),
                        nombre_social=obtener_valor('nombre_social'),
                        fecha_nacimiento=fecha_nacimiento,
                        sexo=self.limpiar_sexo(obtener_valor('sexo')),
                        estado_civil=self.limpiar_estado_civil(obtener_valor('estado_civil')),
                        direccion=obtener_valor('direccion'),
                        numero_telefono1=obtener_valor('numero_telefono1'),
                        numero_telefono2=obtener_valor('numero_telefono2'),
                        comuna=comuna,
                        prevision=prevision,
                        recien_nacido=self.limpiar_bool(obtener_valor('recien_nacido')),
                        extranjero=self.limpiar_bool(obtener_valor('extranjero')),
                        fallecido=self.limpiar_bool(obtener_valor('fallecido')),
                        fecha_fallecimiento=self.limpiar_fecha(obtener_valor('fecha_fallecimiento')),
                        usuario_anterior=usuario_anterior,
                        nombres_padre=obtener_valor('nombres_padre'),
                        nombres_madre=obtener_valor('nombres_madre'),
                        nombre_pareja=obtener_valor('nombre_pareja'),
                        ocupacion=obtener_valor('ocupacion'),
                        representante_legal=obtener_valor('representante_legal'),
                    )

                    if paciente.recien_nacido:
                        rn_creados += 1

                    buffer.append(paciente)
                    ruts_existentes.add(rut)  # Agregar a la lista para evitar duplicados en este proceso
                    creados += 1

                    # Guardar en lotes
                    if len(buffer) >= BATCH_SIZE:
                        try:
                            with transaction.atomic():
                                Paciente.objects.bulk_create(buffer, batch_size=BATCH_SIZE, ignore_conflicts=False)
                            buffer.clear()
                        except Exception as e:
                            # Si hay error, guardar uno por uno para identificar el problema
                            self.stdout.write(self.style.WARNING(f'\nError en bulk_create: {str(e)[:100]}'))
                            exitosos_lote = 0
                            fallidos_lote = 0
                            for p in buffer:
                                try:
                                    with transaction.atomic():
                                        p.save()
                                    exitosos_lote += 1
                                except Exception as e2:
                                    fallidos_lote += 1
                                    # Solo mostrar algunos errores para no saturar
                                    if fallidos_lote <= 5:
                                        self.stdout.write(
                                            self.style.WARNING(f'Error guardando {p.rut}: {str(e2)[:100]}'))
                            buffer.clear()
                            creados -= fallidos_lote  # Ajustar contador
                            errores_validacion += fallidos_lote

                except Exception as e:
                    errores_validacion += 1
                    # Solo mostrar algunos errores
                    if errores_validacion <= 10:
                        self.stdout.write(self.style.WARNING(f'Error en fila {index}: {str(e)[:100]}'))

                pbar.update(1)

            # Guardar cualquier registro restante
            if buffer:
                try:
                    with transaction.atomic():
                        Paciente.objects.bulk_create(buffer, batch_size=BATCH_SIZE, ignore_conflicts=False)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'\nError en último bulk_create: {str(e)[:100]}'))
                    exitosos_lote = 0
                    fallidos_lote = 0
                    for p in buffer:
                        try:
                            with transaction.atomic():
                                p.save()
                            exitosos_lote += 1
                        except Exception as e2:
                            fallidos_lote += 1
                    buffer.clear()
                    creados -= fallidos_lote
                    errores_validacion += fallidos_lote

        # ================== RESUMEN ==================

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('RESUMEN FINAL'))
        self.stdout.write(self.style.SUCCESS(f'Registros en Excel: {total_leidas:,}'))
        self.stdout.write(self.style.WARNING(f'RUTs duplicados en Excel: {duplicados_excel:,}'))
        self.stdout.write(self.style.SUCCESS(f'Procesados exitosamente: {creados:,}'))
        self.stdout.write(self.style.WARNING(f'Omitidos (ya en BD): {omitidos:,}'))
        self.stdout.write(self.style.WARNING(f'Sin RUT: {sin_rut:,}'))
        self.stdout.write(self.style.WARNING(f'Errores de validación: {errores_validacion:,}'))
        self.stdout.write(self.style.SUCCESS(f'RN creados: {rn_creados:,}'))
        self.stdout.write(self.style.WARNING(f'Comuna default usada: {comuna_default_count:,}'))
        self.stdout.write(self.style.WARNING(f'Previsión no encontrada: {prevision_no_encontrada:,}'))

        # Verificar en base de datos
        pacientes_finales = Paciente.objects.count()
        pacientes_nuevos = pacientes_finales - pacientes_existentes_count
        self.stdout.write(self.style.SUCCESS(f'Total pacientes en BD: {pacientes_finales:,}'))
        self.stdout.write(self.style.SUCCESS(f'Pacientes nuevos agregados: {pacientes_nuevos:,}'))

        # Verificar consistencia
        if creados != pacientes_nuevos:
            diferencia = creados - pacientes_nuevos
            self.stdout.write(self.style.WARNING(f'Diferencia entre creados y agregados: {diferencia:,}'))

        self.stdout.write(self.style.SUCCESS('=' * 60))
