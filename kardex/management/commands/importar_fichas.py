import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from tqdm import tqdm

from kardex.models import Ficha, Paciente, Establecimiento
from users.models import UsuarioPersonalizado


def normalize_rut(value):
    """Normaliza un RUT para comparación insensible a formato.
    - Quita puntos, guiones y espacios
    - Convierte a mayúsculas (DV 'K')
    - Elimina ceros a la izquierda del cuerpo numérico
    - Devuelve cuerpo+DV sin separadores (por ejemplo 12345678K o 123456785)
    """
    if value is None:
        return ''
    s = str(value).strip().upper()
    if not s or s == 'NAN':
        return ''
    # Quitar cualquier caracter no alfanumérico (puntos, guiones, espacios, etc.)
    s = ''.join(ch for ch in s if ch.isalnum())
    if not s:
        return ''
    # Separar cuerpo y dígito verificador asumiento ultimo caracter como DV
    cuerpo, dv = s[:-1], s[-1]
    # Eliminar ceros a la izquierda del cuerpo si es numérico
    if cuerpo:
        try:
            cuerpo = str(int(cuerpo))
        except Exception:
            # Si no es puramente numérico, usar como está
            cuerpo = cuerpo
    return f"{cuerpo}{dv}"


class Command(BaseCommand):
    help = 'Importa fichas desde un archivo CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_path',
            type=str,
            help='Ruta al archivo CSV que contiene las fichas'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Tamaño del lote para procesamiento por lotes (default: 1000)'
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        batch_size = options['batch_size']

        try:
            # Leer CSV con pandas
            self.stdout.write(self.style.SUCCESS(f'📖 Leyendo archivo CSV: {csv_path}'))
            df = pd.read_csv(csv_path, delimiter=';', dtype=str)
            total_filas = len(df)
            self.stdout.write(self.style.SUCCESS(f'📊 Total de registros encontrados: {total_filas:,}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Error al leer el archivo CSV: {e}'))
            return

        # Pre-procesar datos
        self.stdout.write(self.style.SUCCESS('🔄 Pre-procesando datos...'))

        # Normalizar RUTs para comparación consistente
        df['paciente_rut'] = df['paciente_id'].apply(lambda x: normalize_rut(x) if pd.notna(x) else '')
        df['usuario_rut'] = df['usuario_id'].apply(lambda x: normalize_rut(x) if pd.notna(x) else '')

        # Convertir establecimiento_id a numérico
        df['establecimiento_id'] = pd.to_numeric(df['establecimiento_id'], errors='coerce')

        # Convertir fecha
        df['fecha_creacion_anterior'] = pd.to_datetime(df['fecha_creacion_anterior'], errors='coerce')

        # Obtener listas únicas para búsquedas optimizadas
        pacientes_ruts = [rut for rut in df['paciente_rut'].unique() if rut]  # Solo RUTs no vacíos
        usuarios_ruts = [rut for rut in df['usuario_rut'].unique() if rut]  # Solo RUTs no vacíos
        establecimientos_ids = df['establecimiento_id'].dropna().unique()

        # Precargar datos en memoria
        self.stdout.write(self.style.SUCCESS('🗃️ Cargando datos en memoria...'))

        # Precargar pacientes - mapear por RUT normalizado para evitar problemas de formato
        pacientes_qs = Paciente.objects.all()
        pacientes_dict = {normalize_rut(paciente.rut): paciente for paciente in pacientes_qs}

        # Precargar users - mapear por username normalizado (asumiendo username es RUT)
        usuarios_qs = UsuarioPersonalizado.objects.all()
        usuarios_dict = {normalize_rut(usuario.username): usuario for usuario in usuarios_qs}

        # Precargar establecimientos
        establecimientos_dict = {
            est.id: est
            for est in Establecimiento.objects.filter(id__in=establecimientos_ids)
        }

        # Verificar fichas existentes en lotes
        self.stdout.write(self.style.SUCCESS('🔍 Verificando fichas existentes...'))
        fichas_existentes = set()

        # Obtener todas las combinaciones únicas de numero_ficha_sistema y establecimiento_id del CSV
        combinaciones_csv = set()
        for _, row in df.iterrows():
            if pd.notna(row['numero_ficha_sistema']) and pd.notna(row['establecimiento_id']):
                combinaciones_csv.add((str(row['numero_ficha_sistema']), int(row['establecimiento_id'])))

        # Consultar la base de datos por lotes para estas combinaciones
        combinaciones_lista = list(combinaciones_csv)
        for i in range(0, len(combinaciones_lista), batch_size):
            batch_combinaciones = combinaciones_lista[i:i + batch_size]

            # Crear consultas separadas para cada establecimiento
            for establecimiento_id in set(est_id for _, est_id in batch_combinaciones):
                fichas_establecimiento = [num for num, est in batch_combinaciones if est == establecimiento_id]
                existentes = Ficha.objects.filter(
                    numero_ficha_sistema__in=fichas_establecimiento,
                    establecimiento_id=establecimiento_id
                ).values_list('numero_ficha_sistema', 'establecimiento_id')

                fichas_existentes.update((str(num), est_id) for num, est_id in existentes)

        total_importados = 0
        total_omitidos = 0
        total_duplicados = 0
        total_pacientes_no_encontrados = 0
        fichas_a_crear = []
        errores_detallados = []

        # Procesar datos
        self.stdout.write(self.style.SUCCESS('🚀 Procesando fichas...'))

        with tqdm(total=total_filas, desc="📋 Procesando fichas", unit="registro") as pbar:
            for index, row in df.iterrows():
                fila_excel = index + 2  # Fila en Excel/CSV

                # Campos del registro actual
                paciente_rut = str(row['paciente_rut'])
                est_id_raw = row['establecimiento_id']
                try:
                    est_id_int = int(est_id_raw) if pd.notna(est_id_raw) else None
                except Exception:
                    est_id_int = None
                numero_ficha = str(row['numero_ficha_sistema'])
                usuario_rut = str(row['usuario_rut'])

                # DEBUG: Mostrar cada 10000 registros para seguimiento
                if index % 10000 == 0 and index > 0:
                    self.stdout.write(self.style.NOTICE(f'🔍 Procesando fila {fila_excel}: {numero_ficha}-{est_id_int}'))

                # Validar RUT del paciente
                if not paciente_rut or paciente_rut == 'nan':
                    self.stdout.write(self.style.WARNING(f'⚠️ Fila {fila_excel}: RUT paciente vacío. Se omite.'))
                    total_omitidos += 1
                    pbar.update(1)
                    continue

                # Buscar paciente por RUT normalizado en el diccionario
                if paciente_rut not in pacientes_dict:
                    self.stdout.write(self.style.WARNING(
                        f'⚠️ Fila {fila_excel}: Paciente con RUT "{paciente_rut}" no encontrado en BD.'))
                    total_pacientes_no_encontrados += 1
                    total_omitidos += 1
                    pbar.update(1)
                    continue

                # Validar establecimiento
                if est_id_int is None:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️ Fila {fila_excel}: Establecimiento ID vacío o inválido. Se omite.'))
                    total_omitidos += 1
                    pbar.update(1)
                    continue

                if est_id_int not in establecimientos_dict:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️ Fila {fila_excel}: Establecimiento ID {est_id_int} no encontrado.'))
                    total_omitidos += 1
                    pbar.update(1)
                    continue

                # Verificar si ya existe
                clave_ficha = (numero_ficha, est_id_int)
                if clave_ficha in fichas_existentes:
                    self.stdout.write(self.style.WARNING(
                        f'⚠️ Fila {fila_excel}: Ficha #{numero_ficha} ya existe para establecimiento {est_id_int}. Se omite.'
                    ))
                    total_duplicados += 1
                    total_omitidos += 1
                    pbar.update(1)
                    continue

                # Obtener objetos
                paciente = pacientes_dict[paciente_rut]
                establecimiento = establecimientos_dict[est_id_int]
                usuario = usuarios_dict.get(usuario_rut)  # Puede ser None si no existe

                # Preparar fecha
                fecha_creacion_anterior = None
                if pd.notna(row['fecha_creacion_anterior']):
                    try:
                        fecha_creacion_anterior = timezone.make_aware(row['fecha_creacion_anterior'])
                    except Exception:
                        pass

                # Preparar observación
                observacion = str(row['observacion']).strip().upper() if pd.notna(row['observacion']) else ''

                # Crear objeto Ficha (sin guardar aún)
                ficha = Ficha(
                    numero_ficha_sistema=numero_ficha,
                    observacion=observacion,
                    usuario=usuario,
                    paciente=paciente,
                    establecimiento=establecimiento,
                    fecha_creacion_anterior=fecha_creacion_anterior
                )
                fichas_a_crear.append(ficha)

                # Crear en lotes para mejor performance
                if len(fichas_a_crear) >= batch_size:
                    try:
                        with transaction.atomic():
                            Ficha.objects.bulk_create(fichas_a_crear, batch_size=batch_size)
                        total_importados += len(fichas_a_crear)
                        self.stdout.write(self.style.SUCCESS(
                            f'✅ Lote creado: {len(fichas_a_crear)} fichas (total: {total_importados})'))
                    except Exception as e:
                        # Si hay error en bulk_create, intentar una por una para identificar el problema
                        self.stdout.write(self.style.ERROR(f'❌ Error en bulk_create: {e}'))
                        self.stdout.write(
                            self.style.ERROR('🔍 Intentando crear una por una para identificar el problema...'))

                        for i, ficha_individual in enumerate(fichas_a_crear):
                            try:
                                ficha_individual.save()
                                total_importados += 1
                            except Exception as e_individual:
                                errores_detallados.append({
                                    'fila': fila_excel - len(fichas_a_crear) + i + 1,
                                    'numero_ficha': ficha_individual.numero_ficha_sistema,
                                    'establecimiento': ficha_individual.establecimiento_id,
                                    'paciente_rut': paciente_rut,
                                    'error': str(e_individual)
                                })
                                self.stdout.write(self.style.ERROR(
                                    f'❌ Error en fila {fila_excel - len(fichas_a_crear) + i + 1}: '
                                    f'Ficha #{ficha_individual.numero_ficha_sistema} - '
                                    f'Establecimiento {ficha_individual.establecimiento_id} - '
                                    f'Paciente {paciente_rut} - '
                                    f'Error: {e_individual}'
                                ))
                                total_omitidos += 1

                        fichas_a_crear = []
                        continue

                    fichas_a_crear = []

                pbar.update(1)
                pbar.set_postfix({
                    'Importadas': total_importados + len(fichas_a_crear),
                    'Omitidas': total_omitidos,
                    'Duplicadas': total_duplicados,
                    'Pacientes NF': total_pacientes_no_encontrados
                })

            # Crear las fichas restantes
            if fichas_a_crear:
                try:
                    with transaction.atomic():
                        Ficha.objects.bulk_create(fichas_a_crear, batch_size=batch_size)
                    total_importados += len(fichas_a_crear)
                    self.stdout.write(self.style.SUCCESS(f'✅ Lote final creado: {len(fichas_a_crear)} fichas'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Error en lote final: {e}'))
                    # Procesar una por una el lote final
                    for i, ficha_individual in enumerate(fichas_a_crear):
                        try:
                            ficha_individual.save()
                            total_importados += 1
                        except Exception as e_individual:
                            errores_detallados.append({
                                'fila': total_filas - len(fichas_a_crear) + i + 1,
                                'numero_ficha': ficha_individual.numero_ficha_sistema,
                                'establecimiento': ficha_individual.establecimiento_id,
                                'paciente_rut': paciente_rut,
                                'error': str(e_individual)
                            })
                            self.stdout.write(self.style.ERROR(
                                f'❌ Error en fila {total_filas - len(fichas_a_crear) + i + 1}: '
                                f'Ficha #{ficha_individual.numero_ficha_sistema} - '
                                f'Establecimiento {ficha_individual.establecimiento_id} - '
                                f'Error: {e_individual}'
                            ))
                            total_omitidos += 1

        # Resumen final
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN FINAL DE IMPORTACIÓN'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'✅ Fichas creadas: {total_importados:,}'))
        self.stdout.write(self.style.WARNING(f'⚠️ Fichas omitidas: {total_omitidos:,}'))
        self.stdout.write(self.style.WARNING(f'🔄 Duplicados detectados: {total_duplicados:,}'))
        self.stdout.write(self.style.WARNING(f'❌ Pacientes no encontrados: {total_pacientes_no_encontrados:,}'))
        self.stdout.write(self.style.SUCCESS(f'📈 Eficiencia: {(total_importados / total_filas * 100):.1f}%'))

        if errores_detallados:
            self.stdout.write(self.style.ERROR('\n❌ ERRORES DETALLADOS:'))
            for error in errores_detallados[:10]:  # Mostrar solo los primeros 10 errores
                self.stdout.write(self.style.ERROR(
                    f'  Fila {error["fila"]}: Ficha #{error["numero_ficha"]} - '
                    f'Establecimiento {error["establecimiento"]} - '
                    f'Paciente {error["paciente_rut"]} - '
                    f'Error: {error["error"]}'
                ))
            if len(errores_detallados) > 10:
                self.stdout.write(self.style.ERROR(f'  ... y {len(errores_detallados) - 10} errores más'))

        self.stdout.write(self.style.SUCCESS('=' * 60))
