import pandas as pd
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.timezone import make_aware
from tqdm import tqdm

from kardex.models import (
    MovimientoFicha,
    ServicioClinico,
    Ficha,
    Profesional,
    Establecimiento,
    UsuarioAnterior,
)


class Command(BaseCommand):
    help = 'Importa movimientos de fichas desde un archivo CSV.'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_path',
            type=str,
            help='Ruta al archivo CSV que contiene los movimientos de fichas',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Tamaño del lote para procesamiento (por defecto: 1000)',
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        batch_size = options['batch_size']

        try:
            self.stdout.write(self.style.SUCCESS(f'📖 Leyendo archivo CSV: {csv_path}'))
            df = pd.read_csv(csv_path, sep=';', dtype=str, engine='python', on_bad_lines='skip')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Error al leer el archivo: {e}'))
            return

        # Limpiar nombres de columnas
        df.columns = df.columns.str.strip()
        total_registros = len(df)

        self.stdout.write(f'📊 Total de registros encontrados: {total_registros:,}')
        self.stdout.write('🔄 Procesando movimientos...')

        movimientos_a_crear = []
        total_importados = 0
        total_actualizados = 0
        total_errores = 0

        # Configurar barra de progreso
        with tqdm(
                total=total_registros,
                desc='📋 Procesando movimientos',
                unit='registro',
                ncols=100
        ) as pbar:

            for index, row in df.iterrows():
                try:
                    # === Limpieza general de datos ===
                    row = row.fillna('')

                    # === Lectura de campos ===
                    establecimiento_id = self.to_int_or_none(row.get('establecimiento'))
                    rut_anterior = str(row.get('rut_anterior', '')).strip() or 'SIN RUT'
                    numero_ficha_sistema = self.to_int_or_none(row.get('ficha'))  # Cambiado el nombre

                    fecha_envio = self.parse_fecha(row.get('fecha_envio'))
                    fecha_recepcion = self.parse_fecha(row.get('fecha_recepcion'))

                    usuario_envio_anterior_rut = str(row.get('usuario_envio_anterior', '')).strip()
                    usuario_recepcion_anterior_rut = str(row.get('usuario_recepcion_anterior', '')).strip()
                    profesional_recepcion_rut = str(row.get('profesional_recepcion', '')).strip()
                    servicio_recepcion_id = self.to_int_or_none(row.get('servicio_clinico_recepcion'))

                    observacion_envio = str(row.get('observacion_envio', '')).strip()
                    observacion_recepcion = str(row.get('observacion_recepcion', '')).strip()
                    observacion_traspaso = str(row.get('observacion_traspaso', '')).strip()

                    # === Estado ===
                    estado_raw = str(row.get('estado_recepcion', '')).strip().upper()
                    estado_recepcion = self.map_estado(estado_raw)
                    estado_envio = 'ENVIADO'
                    estado_traspaso = 'SIN TRASPASO'

                    # === Relaciones - CAMBIO IMPORTANTE AQUÍ ===
                    # Buscar la ficha por numero_ficha_sistema en lugar de id
                    ficha_obj = Ficha.objects.filter(
                        numero_ficha_sistema=numero_ficha_sistema).first() if numero_ficha_sistema else None
                    if not ficha_obj:
                        self.stdout.write(self.style.WARNING(
                            f'⚠️ Fila {index + 2}: Ficha con número {numero_ficha_sistema} no encontrada. Se omite.'
                        ))
                        total_errores += 1
                        pbar.update(1)
                        continue

                    establecimiento = self.safe_get(Establecimiento, establecimiento_id, 'establecimiento', index)
                    servicio_recepcion = self.safe_get(ServicioClinico, servicio_recepcion_id,
                                                       'servicio_clinico_recepcion',
                                                       index)
                    usuario_envio_anterior = self.safe_get_by_rut(UsuarioAnterior, usuario_envio_anterior_rut,
                                                                  'usuario_envio_anterior', index)
                    usuario_recepcion_anterior = self.safe_get_by_rut(UsuarioAnterior, usuario_recepcion_anterior_rut,
                                                                      'usuario_recepcion_anterior', index)

                    # === Lógica especial para profesional_recepcion ===
                    profesional_recepcion = self.safe_get_by_rut(Profesional, profesional_recepcion_rut,
                                                                 'profesional_recepcion', index)
                    if not profesional_recepcion and profesional_recepcion_rut not in ('', '0', 'SIN RUT', 'NULL'):
                        rut_anterior_profesional = profesional_recepcion_rut
                    else:
                        rut_anterior_profesional = 'SIN RUT'

                    # === Crear movimiento ===
                    movimiento = MovimientoFicha(
                        ficha=ficha_obj,
                        fecha_envio=fecha_envio,
                        fecha_recepcion=fecha_recepcion,
                        observacion_envio=observacion_envio,
                        observacion_recepcion=observacion_recepcion,
                        observacion_traspaso=observacion_traspaso,
                        estado_envio=estado_envio,
                        estado_recepcion=estado_recepcion,
                        estado_traspaso=estado_traspaso,
                        servicio_clinico_recepcion=servicio_recepcion,
                        usuario_envio_anterior=usuario_envio_anterior,
                        usuario_recepcion_anterior=usuario_recepcion_anterior,
                        profesional_recepcion=profesional_recepcion,
                        establecimiento=establecimiento,
                        rut_anterior=rut_anterior or 'SIN RUT',
                        rut_anterior_profesional=rut_anterior_profesional,
                    )

                    movimientos_a_crear.append(movimiento)

                    # Procesar por lotes
                    if len(movimientos_a_crear) >= batch_size:
                        creados, actualizados = self.procesar_lote(movimientos_a_crear)
                        total_importados += creados
                        total_actualizados += actualizados
                        movimientos_a_crear = []

                        # Actualizar barra de progreso con estadísticas
                        pbar.set_postfix({
                            'Importados': total_importados,
                            'Actualizados': total_actualizados,
                            'Errores': total_errores
                        })

                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'❌ Error en fila {index + 2}: {str(e)}'
                    ))
                    total_errores += 1

                pbar.update(1)

            # Procesar último lote
            if movimientos_a_crear:
                creados, actualizados = self.procesar_lote(movimientos_a_crear)
                total_importados += creados
                total_actualizados += actualizados

        # Mostrar resumen final
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 50))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN FINAL DE IMPORTACIÓN'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS(f'✅ Movimientos creados: {total_importados:,}'))
        self.stdout.write(self.style.SUCCESS(f'🔄 Movimientos actualizados: {total_actualizados:,}'))
        self.stdout.write(self.style.SUCCESS(f'❌ Errores: {total_errores:,}'))
        self.stdout.write(self.style.SUCCESS(
            f'📈 Eficiencia: {((total_importados + total_actualizados) / total_registros * 100):.1f}%'))

    def procesar_lote(self, movimientos):
        """Procesa un lote de movimientos usando bulk_create con manejo de duplicados"""
        creados = 0
        actualizados = 0

        try:
            # Intentar crear en lote
            MovimientoFicha.objects.bulk_create(movimientos, ignore_conflicts=False)
            creados = len(movimientos)
            self.stdout.write(self.style.SUCCESS(f'✅ Lote creado: {len(movimientos)} movimientos'))

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️ Error en bulk_create: {e}'))
            self.stdout.write('🔍 Intentando crear una por una para identificar el problema...')

            # Crear uno por uno para identificar errores específicos
            for movimiento in movimientos:
                try:
                    obj, created = MovimientoFicha.objects.update_or_create(
                        ficha=movimiento.ficha,
                        fecha_envio=movimiento.fecha_envio,
                        defaults={
                            'fecha_recepcion': movimiento.fecha_recepcion,
                            'observacion_envio': movimiento.observacion_envio,
                            'observacion_recepcion': movimiento.observacion_recepcion,
                            'observacion_traspaso': movimiento.observacion_traspaso,
                            'estado_envio': movimiento.estado_envio,
                            'estado_recepcion': movimiento.estado_recepcion,
                            'estado_traspaso': movimiento.estado_traspaso,
                            'servicio_clinico_recepcion': movimiento.servicio_clinico_recepcion,
                            'usuario_envio_anterior': movimiento.usuario_envio_anterior,
                            'usuario_recepcion_anterior': movimiento.usuario_recepcion_anterior,
                            'profesional_recepcion': movimiento.profesional_recepcion,
                            'establecimiento': movimiento.establecimiento,
                            'rut_anterior': movimiento.rut_anterior,
                            'rut_anterior_profesional': movimiento.rut_anterior_profesional,
                        }
                    )
                    if created:
                        creados += 1
                    else:
                        actualizados += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'❌ Error creando movimiento para ficha #{movimiento.ficha.id} (sistema: {movimiento.ficha.numero_ficha_sistema}): {e}'
                    ))

        return creados, actualizados

    # === Utilidades (mantener las mismas) ===

    def safe_get(self, model, pk, nombre, index):
        """Obtiene instancia por PK si existe."""
        if not pk:
            return None
        obj = model.objects.filter(id=pk).first()
        if not obj:
            self.stdout.write(self.style.WARNING(f'⚠️ Fila {index + 2}: {nombre} ID {pk} no encontrado.'))
        return obj

    def safe_get_by_rut(self, model, rut, nombre, index):
        """Obtiene instancia por campo RUT si aplica."""
        if not rut or rut.strip() in ('', '0', 'SIN RUT', 'NULL'):
            return None
        obj = model.objects.filter(rut=rut.strip()).first()
        if not obj:
            self.stdout.write(self.style.WARNING(f'⚠️ Fila {index + 2}: {nombre} con RUT {rut} no encontrado. {model}'))
        return obj

    def parse_fecha(self, value):
        """Convierte fechas del CSV a datetime aware (con zona horaria)."""
        if pd.isna(value) or value == '' or str(value).upper() == 'NULL':
            return timezone.now()
        try:
            if isinstance(value, pd.Timestamp):
                dt = value.to_pydatetime()
            else:
                dt = pd.to_datetime(value)
            if timezone.is_naive(dt):
                dt = make_aware(dt, timezone.get_current_timezone())
            return dt
        except Exception:
            return timezone.now()

    def to_int_or_none(self, value):
        try:
            if pd.isna(value) or str(value).strip() in ('', 'NULL'):
                return None
            return int(value)
        except Exception:
            return None

    def map_estado(self, estado):
        """Mapea las letras o abreviaciones del CSV a tus choices con debug."""
        estado_str = str(estado).upper().strip()

        if estado_str in ['R', 'RECIBIDO']:
            return 'RECIBIDO'
        elif estado_str in ['E', 'ENVIADO']:
            return 'ENVIADO'
        elif estado_str in ['P', 'PENDIENTE']:
            return 'EN ESPERA'
        else:
            return 'EN ESPERA'
