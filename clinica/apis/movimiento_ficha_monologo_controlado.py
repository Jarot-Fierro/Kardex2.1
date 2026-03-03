from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from clinica.models.ficha import Ficha
from clinica.models.movimiento_ficha_monologo_controlado import MovimientoMonologoControlado
from establecimientos.models.servicio_clinico import ServicioClinico
from personas.models.pacientes import Paciente
from personas.models.profesionales import Profesional


class RegistrarSalidaAPI(APIView):
    def post(self, request):
        rut = request.data.get('rut')
        servicio_clinico_destino_id = request.data.get('servicio_clinico_destino')
        profesional_id = request.data.get('profesional')
        observacion_salida = request.data.get('observacion_salida')
        fecha_salida = request.data.get('fecha_salida')

        # Validaciones básicas
        if not rut or not servicio_clinico_destino_id or not profesional_id:
            return Response({'error': 'RUT, Servicio Clínico Destino y Profesional son obligatorios.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1. Obtener Paciente y Ficha en el establecimiento del usuario
                try:
                    paciente = Paciente.objects.get(rut=rut)
                except Paciente.DoesNotExist:
                    return Response({'error': 'Paciente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

                establecimiento = request.user.establecimiento
                if not establecimiento:
                    return Response({'error': 'Usuario no tiene establecimiento asignado.'},
                                    status=status.HTTP_403_FORBIDDEN)

                try:
                    ficha = Ficha.objects.get(paciente=paciente, establecimiento=establecimiento)
                except Ficha.DoesNotExist:
                    return Response({'error': 'Ficha no encontrada en este establecimiento.'},
                                    status=status.HTTP_404_NOT_FOUND)

                # 2. Validar que no exista movimiento en estado 'E'
                if MovimientoMonologoControlado.objects.filter(ficha=ficha, estado='E', status=True).exists():
                    return Response({'error': 'Ya existe un movimiento en tránsito para esta ficha.'},
                                    status=status.HTTP_400_BAD_REQUEST)

                # 3. Validar servicio clinico
                try:
                    servicio_destino = ServicioClinico.objects.get(pk=servicio_clinico_destino_id)
                except ServicioClinico.DoesNotExist:
                    return Response({'error': 'Servicio clínico destino no válido.'},
                                    status=status.HTTP_400_BAD_REQUEST)

                # 4. Validar profesional
                try:
                    profesional = Profesional.objects.get(pk=profesional_id)
                except Profesional.DoesNotExist:
                    return Response({'error': 'Profesional no válido.'}, status=status.HTTP_400_BAD_REQUEST)

                # 5. Crear Movimiento
                movimiento = MovimientoMonologoControlado(
                    rut=rut,
                    numero_ficha=ficha.numero_ficha_sistema,
                    rut_paciente=paciente,
                    ficha=ficha,
                    establecimiento=establecimiento,
                    servicio_clinico_destino=servicio_destino,
                    profesional=profesional,
                    observacion_salida=observacion_salida,
                    fecha_salida=fecha_salida if fecha_salida else timezone.localtime(),
                    usuario_entrega=request.user.username,
                    estado='E'
                )
                movimiento.save()
                print(movimiento.fecha_salida)

                return Response(
                    {'success': True, 'message': 'Salida registrada correctamente.', 'movimiento_id': movimiento.id},
                    status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RegistrarRecepcionAPI(APIView):
    def post(self, request):
        movimiento_id = request.data.get('movimiento_id')
        observacion_entrada = request.data.get('observacion_recepcion')
        fecha_entrada = request.data.get('fecha_entrada')

        if not movimiento_id:
            return Response({'error': 'ID de movimiento no proporcionado.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                try:
                    movimiento = MovimientoMonologoControlado.objects.select_related('establecimiento').get(
                        pk=movimiento_id)
                except MovimientoMonologoControlado.DoesNotExist:
                    return Response({'error': 'Movimiento no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

                # Validaciones
                if movimiento.estado != 'E':
                    return Response({'error': 'El movimiento no está en estado Enviado (E).'},
                                    status=status.HTTP_400_BAD_REQUEST)

                if movimiento.establecimiento != request.user.establecimiento:
                    return Response({'error': 'El movimiento no pertenece a su establecimiento.'},
                                    status=status.HTTP_403_FORBIDDEN)

                # Actualizar
                movimiento.usuario_entrada = request.user.username
                movimiento.observacion_entrada = observacion_entrada
                movimiento.fecha_entrada = fecha_entrada if fecha_entrada else timezone.localtime()
                movimiento.estado = 'R'
                movimiento.save()

                return Response({'success': True, 'message': 'Recepción registrada correctamente.'},
                                status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RegistrarTraspasoAPI(APIView):
    def post(self, request):
        movimiento_id = request.data.get('movimiento_id_hidden') or request.data.get('movimiento_id')
        servicio_clinico_destino_id = request.data.get('servicio_clinico_destino')
        profesional_id = request.data.get('profesional')
        observacion_traspaso = request.data.get('observacion_traspaso')
        fecha_salida = request.data.get('fecha_salida')

        # Validaciones básicas
        if not movimiento_id or not servicio_clinico_destino_id or not profesional_id:
            return Response({'error': 'Movimiento, Servicio Clínico Destino y Profesional son obligatorios.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1. Obtener el Movimiento
                try:
                    movimiento = MovimientoMonologoControlado.objects.get(pk=movimiento_id)
                except MovimientoMonologoControlado.DoesNotExist:
                    return Response({'error': 'Movimiento no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

                # 2. Validar servicio clinico
                try:
                    servicio_destino = ServicioClinico.objects.get(pk=servicio_clinico_destino_id)
                except ServicioClinico.DoesNotExist:
                    return Response({'error': 'Servicio clínico destino no válido.'},
                                    status=status.HTTP_400_BAD_REQUEST)

                # 3. Validar profesional
                try:
                    profesional = Profesional.objects.get(pk=profesional_id)
                except Profesional.DoesNotExist:
                    return Response({'error': 'Profesional no válido.'}, status=status.HTTP_400_BAD_REQUEST)

                # 4. Actualizar Movimiento
                movimiento.servicio_clinico_destino = servicio_destino
                movimiento.profesional = profesional
                movimiento.observacion_traspaso = observacion_traspaso

                # Si el usuario ingresó una fecha, se actualiza. Si no, se mantiene la original.
                if fecha_salida:
                    movimiento.fecha_salida = fecha_salida

                movimiento.save()

                return Response(
                    {'success': True, 'message': 'Traspaso actualizado correctamente.', 'movimiento_id': movimiento.id},
                    status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
