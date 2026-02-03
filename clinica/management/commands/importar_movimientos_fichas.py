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


# ================= UTILIDADES =================

def normalize_rut(value):
    if value is None:
        return ''
    s = str(value).strip().upper()
    if not s or s in ('NAN', 'NULL', 'SIN RUT', '0', '0.0'):
        return ''
    s = s.replace('.', '').replace('-', '').replace(' ', '')
    return s


def clean_text(value):
    if value is None:
        return ''
    s = str(value).strip()
    if s.upper() in ('NAN', 'NULL', 'NONE'):
        return ''
    return s


def safe_make_aware(dt):
    """Convertir datetime a aware de forma segura, manejando NaT"""
    if pd.isna(dt) or dt is None:
        return None
    try:
        return make_aware(dt)
    except (ValueError, AttributeError):
        return None


# ================= COMMAND =================

class Command(BaseCommand):
    help = 'Importa movimientos de fichas desde CSV'

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
            engine='python',
            quotechar='"',
            on_bad_lines='skip',
            keep_default_na=False
        )

        df.columns = df.columns.str.strip()
        total_filas = len(df)

        self.stdout.write(self.style.SUCCESS(f'📊 Total de filas en CSV: {total_filas:,}'))
        self.stdout.write(self.style.SUCCESS(f'📋 Columnas encontradas: {", ".join(df.columns.tolist())}'))

        # ================= PREPROCESAMIENTO =================

        # Normalizar RUTs
        for rut_col in ['rut_paciente', 'usuario_entrega', 'usuario_entrada', 'profesional']:
            if rut_col in df.columns:
                df[rut_col] = df[rut_col].apply(normalize_rut)

        # Convertir números (importante: servicio_clinico es código, no ID)
        numeric_columns = ['establecimiento', 'ficha']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Servicio clínico se mantiene como float/int para buscar por código
        if 'servicio_clinico' in df.columns:
            df['servicio_clinico'] = pd.to_numeric(df['servicio_clinico'], errors='coerce')

        # Convertir fechas
        if 'fecha_salida' in df.columns:
            df['fecha_salida'] = pd.to_datetime(
                df['fecha_salida'],
                errors='coerce',
                format='mixed'
            )
            invalid_dates = df['fecha_salida'].isna().sum()
            if invalid_dates > 0:
                self.stdout.write(self.style.WARNING(f'⚠️ Fechas de salida inválidas: {invalid_dates}'))

        if 'fecha_entrada' in df.columns:
            df['fecha_entrada'] = pd.to_datetime(
                df['fecha_entrada'],
                errors='coerce',
                format='mixed'
            )
            invalid_dates = df['fecha_entrada'].isna().sum()
            if invalid_dates > 0:
                self.stdout.write(self.style.WARNING(f'⚠️ Fechas de entrada inválidas: {invalid_dates}'))

        # ================= CACHÉS =================

        self.stdout.write(self.style.SUCCESS('📦 Cargando datos de referencia...'))

        # Cargar fichas
        fichas_dict = {
            (f.numero_ficha_sistema, f.establecimiento_id): f
            for f in Ficha.objects.all()
        }
        self.stdout.write(self.style.SUCCESS(f'✅ Fichas cargadas: {len(fichas_dict):,}'))

        # Cargar establecimientos
        establecimientos_dict = {e.id: e for e in Establecimiento.objects.all()}
        self.stdout.write(self.style.SUCCESS(f'✅ Establecimientos cargados: {len(establecimientos_dict):,}'))

        # Cargar servicios clínicos POR CÓDIGO (no por ID)
        servicios_por_codigo = {}
        servicios_sin_codigo = []
        for s in ServicioClinico.objects.all():
            if s.codigo is not None:
                servicios_por_codigo[s.codigo] = s
            else:
                servicios_sin_codigo.append(s.id)

        if servicios_sin_codigo:
            self.stdout.write(self.style.WARNING(f'⚠️ Servicios sin código: {len(servicios_sin_codigo)}'))

        self.stdout.write(
            self.style.SUCCESS(f'✅ Servicios clínicos cargados por código: {len(servicios_por_codigo):,}'))
        self.stdout.write(self.style.SUCCESS(f'📝 Códigos disponibles: {list(servicios_por_codigo.keys())[:10]}...'))

        # Cargar servicios clínicos "ARCHIVO" por establecimiento
        # Mapeo de establecimiento_id -> servicio_clinico "ARCHIVO"
        servicios_archivo_por_establecimiento = {}
        servicios_archivo = ServicioClinico.objects.filter(nombre='ARCHIVO')

        for servicio_archivo in servicios_archivo:
            # Obtener el establecimiento relacionado con este servicio ARCHIVO
            # Asumiendo que hay una relación directa o indirecta
            if hasattr(servicio_archivo, 'establecimiento') and servicio_archivo.establecimiento:
                servicios_archivo_por_establecimiento[servicio_archivo.establecimiento.id] = servicio_archivo
            # También buscar por nombre del establecimiento en el nombre del servicio
            elif servicio_archivo.descripcion:
                # Buscar establecimientos en la descripción
                for establecimiento_id, establecimiento in establecimientos_dict.items():
                    if establecimiento.nombre and establecimiento.nombre in servicio_archivo.descripcion:
                        servicios_archivo_por_establecimiento[establecimiento_id] = servicio_archivo
                        break

        self.stdout.write(
            self.style.SUCCESS(f'✅ Servicios ARCHIVO cargados: {len(servicios_archivo_por_establecimiento):,}'))

        # Si no encontramos por la lógica anterior, usar el mapeo manual basado en tu información
        if len(servicios_archivo_por_establecimiento) == 0:
            # Mapeo manual de establecimiento_id -> servicio_clinico_id para ARCHIVO
            mapeo_manual_archivo = {
                233: 381,  # HOSPITAL DE ARAUCO -> ARCHIVO id 381
                4: 380,  # HOSPITAL DE CONTULMO -> ARCHIVO id 380
                # Agrega otros establecimientos según corresponda
            }

            # Buscar los servicios ARCHIVO por ID
            for establecimiento_id, servicio_id in mapeo_manual_archivo.items():
                try:
                    servicio = ServicioClinico.objects.get(id=servicio_id, nombre='ARCHIVO')
                    servicios_archivo_por_establecimiento[establecimiento_id] = servicio
                except ServicioClinico.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f'⚠️ Servicio ARCHIVO con ID {servicio_id} no encontrado para establecimiento {establecimiento_id}'))

        if servicios_archivo_por_establecimiento:
            self.stdout.write(self.style.SUCCESS('📋 Servicios ARCHIVO por establecimiento:'))
            for est_id, servicio in servicios_archivo_por_establecimiento.items():
                self.stdout.write(self.style.SUCCESS(f'  Establecimiento {est_id}: Servicio ARCHIVO ID {servicio.id}'))

        # Cargar usuarios anteriores
        usuarios_ant_dict = {normalize_rut(u.rut): u for u in UsuarioAnterior.objects.all()}
        self.stdout.write(self.style.SUCCESS(f'✅ Usuarios anteriores cargados: {len(usuarios_ant_dict):,}'))

        # Cargar profesionales
        profesionales_dict = {normalize_rut(p.rut): p for p in Profesional.objects.all()}
        self.stdout.write(self.style.SUCCESS(f'✅ Profesionales cargados: {len(profesionales_dict):,}'))

        # Obtener movimientos existentes para evitar duplicados
        movimientos_existentes = set(
            MovimientoFicha.objects.values_list('ficha_id', 'fecha_envio')
        )
        self.stdout.write(self.style.SUCCESS(f'✅ Movimientos existentes: {len(movimientos_existentes):,}'))

        movimientos_a_crear = []
        errores = []

        total_importados = 0
        total_omitidos = 0
        total_duplicados = 0
        total_errores = 0
        total_servicios_no_encontrados = 0

        # Contadores para estadísticas
        contador_e = 0
        contador_r = 0
        contador_sin_estado = 0

        self.stdout.write(self.style.SUCCESS('🚀 Importando movimientos...'))

        with tqdm(total=total_filas, unit='reg', desc='Procesando') as pbar:
            for idx, row in df.iterrows():
                try:
                    # Obtener datos básicos
                    ficha_num = row.get('ficha')
                    est_id = row.get('establecimiento')

                    # Verificar que tenemos los datos necesarios
                    if pd.isna(ficha_num) or pd.isna(est_id):
                        total_omitidos += 1
                        errores.append({
                            'fila_csv': idx + 2,
                            'motivo': 'DATOS_INCOMPLETOS',
                            'ficha': ficha_num,
                            'establecimiento': est_id
                        })
                        pbar.update(1)
                        continue

                    # Convertir a enteros
                    try:
                        ficha_num_int = int(ficha_num)
                        est_id_int = int(est_id)
                    except (ValueError, TypeError):
                        total_omitidos += 1
                        errores.append({
                            'fila_csv': idx + 2,
                            'motivo': 'DATOS_NUMERICOS_INVALIDOS',
                            'ficha': ficha_num,
                            'establecimiento': est_id
                        })
                        pbar.update(1)
                        continue

                    # Buscar ficha
                    ficha = fichas_dict.get((ficha_num_int, est_id_int))
                    if not ficha:
                        total_omitidos += 1
                        errores.append({
                            'fila_csv': idx + 2,
                            'motivo': 'FICHA_NO_EXISTE',
                            'ficha': ficha_num_int,
                            'establecimiento': est_id_int
                        })
                        pbar.update(1)
                        continue

                    # Fecha de envío (con manejo seguro)
                    fecha_envio = safe_make_aware(row.get('fecha_salida'))

                    # Verificar duplicado
                    clave = (ficha.id, fecha_envio)
                    if clave in movimientos_existentes:
                        total_omitidos += 1
                        total_duplicados += 1
                        pbar.update(1)
                        continue

                    movimientos_existentes.add(clave)

                    # ================= LÓGICA DE ESTADOS =================

                    estado_csv = clean_text(row.get('estado', '')).upper()

                    # Determinar si es Enviado (E) o Recibido (R)
                    es_enviado = estado_csv == 'E'
                    es_recibido = estado_csv == 'R'

                    # Estadísticas
                    if es_enviado:
                        contador_e += 1
                    elif es_recibido:
                        contador_r += 1
                    else:
                        contador_sin_estado += 1
                        # Si no tiene estado, asumimos que está enviado pero no recibido
                        es_enviado = True
                        es_recibido = False

                    # ================= OBTENER DATOS DE REFERENCIA =================

                    # Establecimiento
                    establecimiento = establecimientos_dict.get(est_id_int)

                    # Servicio clínico del CSV (envío/recepción)
                    servicio_codigo = row.get('servicio_clinico')
                    servicio_csv = None
                    if not pd.isna(servicio_codigo):
                        try:
                            # Convertir a entero (manejar "2.0" como 2)
                            if isinstance(servicio_codigo, float):
                                codigo_int = int(servicio_codigo)
                            else:
                                codigo_int = int(float(servicio_codigo))

                            servicio_csv = servicios_por_codigo.get(codigo_int)
                            if not servicio_csv:
                                total_servicios_no_encontrados += 1
                                self.stdout.write(self.style.WARNING(
                                    f'⚠️ Servicio con código {codigo_int} no encontrado (fila {idx + 2})'
                                ))
                        except (ValueError, TypeError, AttributeError) as e:
                            servicio_csv = None
                            self.stdout.write(self.style.WARNING(
                                f'⚠️ Error al procesar código de servicio: {servicio_codigo} (fila {idx + 2}): {str(e)}'
                            ))

                    # Servicio clínico ARCHIVO según establecimiento
                    servicio_archivo = servicios_archivo_por_establecimiento.get(est_id_int)
                    if not servicio_archivo:
                        self.stdout.write(self.style.WARNING(
                            f'⚠️ No se encontró servicio ARCHIVO para establecimiento {est_id_int} (fila {idx + 2})'
                        ))
                        # Intentar encontrar cualquier servicio ARCHIVO como fallback
                        servicios_archivo_fallback = ServicioClinico.objects.filter(nombre='ARCHIVO').first()
                        if servicios_archivo_fallback:
                            servicio_archivo = servicios_archivo_fallback
                            servicios_archivo_por_establecimiento[est_id_int] = servicio_archivo

                    # Usuarios anteriores
                    usuario_entrega_ant = usuarios_ant_dict.get(normalize_rut(row.get('usuario_entrega', '')))
                    usuario_entrada_ant = usuarios_ant_dict.get(normalize_rut(row.get('usuario_entrada', '')))

                    # Profesional
                    profesional = profesionales_dict.get(normalize_rut(row.get('profesional', '')))

                    # ================= CONFIGURAR CAMPOS SEGÚN ESTADO =================

                    # LÓGICA MODIFICADA:
                    # - Servicio ARCHIVO siempre se asigna al establecimiento
                    # - Servicio del CSV se usa para envío/recepción si está disponible

                    # Fecha de recepción (solo si está recibido)
                    fecha_recepcion = None
                    if es_recibido:
                        fecha_recepcion = safe_make_aware(row.get('fecha_entrada'))
                        # Si no hay fecha de entrada, usar fecha de salida
                        if not fecha_recepcion:
                            fecha_recepcion = fecha_envio

                    # Campos para ENVÍO (siempre se llenan si está enviado o recibido)
                    estado_envio_final = 'ENVIADO' if (es_enviado or es_recibido) else ''

                    # Servicio para envío: primero intentar servicio del CSV, luego ARCHIVO
                    servicio_envio_final = servicio_csv if servicio_csv else servicio_archivo

                    profesional_envio_final = profesional if (es_enviado or es_recibido) else None
                    usuario_envio_ant_final = usuario_entrega_ant if (es_enviado or es_recibido) else None

                    # Campos para RECEPCIÓN (solo si está recibido)
                    estado_recepcion_final = 'RECIBIDO' if es_recibido else 'EN ESPERA'

                    # Servicio para recepción: mismo que para envío
                    servicio_recepcion_final = servicio_csv if servicio_csv else servicio_archivo

                    profesional_recepcion_final = profesional if es_recibido else None
                    usuario_recepcion_ant_final = usuario_entrada_ant if es_recibido else None

                    # Si está recibido pero no hay usuario_entrada, usar usuario_entrega
                    if es_recibido and not usuario_recepcion_ant_final:
                        usuario_recepcion_ant_final = usuario_entrega_ant

                    # ================= CREAR MOVIMIENTO =================

                    movimiento = MovimientoFicha(
                        ficha=ficha,
                        establecimiento=establecimiento,

                        # Datos de ENVÍO
                        fecha_envio=fecha_envio,
                        estado_envio=estado_envio_final,
                        servicio_clinico_envio=servicio_envio_final,
                        profesional_envio=profesional_envio_final,
                        usuario_envio_anterior=usuario_envio_ant_final,
                        observacion_envio=clean_text(row.get('observacion_salida', '')),

                        # Datos de RECEPCIÓN
                        fecha_recepcion=fecha_recepcion,
                        estado_recepcion=estado_recepcion_final,
                        servicio_clinico_recepcion=servicio_recepcion_final,
                        profesional_recepcion=profesional_recepcion_final,
                        usuario_recepcion_anterior=usuario_recepcion_ant_final,
                        observacion_recepcion=clean_text(row.get('observacion_entrada', '')),

                        # Datos de TRASPASO (siempre sin traspaso en esta importación)
                        estado_traspaso='SIN TRASPASO',
                        observacion_traspaso=clean_text(row.get('observacion_traspaso', '')),

                        # RUTs antiguos (para auditoría)
                        rut_anterior=normalize_rut(row.get('rut_paciente', '')) or 'SIN RUT',
                        rut_anterior_profesional=normalize_rut(row.get('profesional', '')) or 'SIN RUT'
                    )

                    movimientos_a_crear.append(movimiento)

                    # Insertar en lote
                    if len(movimientos_a_crear) >= batch_size:
                        try:
                            with transaction.atomic():
                                MovimientoFicha.objects.bulk_create(movimientos_a_crear, ignore_conflicts=True)
                            total_importados += len(movimientos_a_crear)
                            movimientos_a_crear.clear()
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'❌ Error en batch: {str(e)}'))
                            total_errores += len(movimientos_a_crear)
                            movimientos_a_crear.clear()

                except Exception as e:
                    total_errores += 1
                    errores.append({
                        'fila_csv': idx + 2,
                        'motivo': f'ERROR_GENERAL: {str(e)}',
                        'ficha': row.get('ficha', ''),
                        'establecimiento': row.get('establecimiento', '')
                    })

                pbar.update(1)

        # Insertar los registros restantes
        if movimientos_a_crear:
            try:
                with transaction.atomic():
                    MovimientoFicha.objects.bulk_create(movimientos_a_crear, ignore_conflicts=True)
                total_importados += len(movimientos_a_crear)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error en último batch: {str(e)}'))
                total_errores += len(movimientos_a_crear)

        # Guardar errores si los hay
        if errores:
            error_df = pd.DataFrame(errores)
            error_path = 'errores_importacion_movimientos.csv'
            error_df.to_csv(error_path, index=False, encoding='utf-8-sig')
            self.stdout.write(self.style.WARNING(f'⚠️ Se guardaron {len(errores):,} errores en: {error_path}'))

        # Mostrar resumen
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN FINAL'))
        self.stdout.write(self.style.SUCCESS(f'✅ Importados: {total_importados:,}'))
        self.stdout.write(self.style.WARNING(f'⚠️ Omitidos: {total_omitidos:,}'))
        self.stdout.write(self.style.WARNING(f'🔁 Duplicados: {total_duplicados:,}'))
        self.stdout.write(self.style.WARNING(f'🏥 Servicios no encontrados: {total_servicios_no_encontrados:,}'))
        self.stdout.write(self.style.ERROR(f'❌ Errores: {total_errores:,}'))

        # Mostrar estadísticas de estados
        self.stdout.write(self.style.SUCCESS('\n📋 ESTADÍSTICAS DE ESTADOS CSV:'))
        self.stdout.write(self.style.SUCCESS(f'  E (Enviado): {contador_e:,}'))
        self.stdout.write(self.style.SUCCESS(f'  R (Recibido): {contador_r:,}'))
        self.stdout.write(self.style.WARNING(f'  Sin estado: {contador_sin_estado:,}'))

        if total_importados > 0:
            self.stdout.write(self.style.SUCCESS(
                f'📈 Tasa de éxito: {(total_importados / (total_importados + total_omitidos + total_errores) * 100):.1f}%'))

        self.stdout.write(self.style.SUCCESS('=' * 60))

        # Mostrar distribución de estados finales
        self.stdout.write(self.style.SUCCESS('\n📋 DISTRIBUCIÓN DE ESTADOS FINALES:'))
        if total_importados > 0:
            movimientos_importados = MovimientoFicha.objects.order_by('-id')[:total_importados]
            estados_envio = movimientos_importados.values_list('estado_envio', flat=True)
            estados_recepcion = movimientos_importados.values_list('estado_recepcion', flat=True)

            from collections import Counter
            estado_envio_counter = Counter(estados_envio)
            estado_recepcion_counter = Counter(estados_recepcion)

            self.stdout.write(self.style.SUCCESS('  ENVÍO:'))
            for estado, count in estado_envio_counter.items():
                if estado:  # Solo mostrar si no está vacío
                    self.stdout.write(self.style.SUCCESS(f'    {estado}: {count:,}'))

            self.stdout.write(self.style.SUCCESS('  RECEPCIÓN:'))
            for estado, count in estado_recepcion_counter.items():
                self.stdout.write(self.style.SUCCESS(f'    {estado}: {count:,}'))
