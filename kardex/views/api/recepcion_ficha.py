from django.utils import timezone
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from kardex.models import MovimientoFicha, Ficha, Paciente, Establecimiento, ServicioClinico


class EstablecimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Establecimiento
        fields = '__all__'


class PacienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = '__all__'


class FichaSerializer(serializers.ModelSerializer):
    paciente = PacienteSerializer()
    establecimiento = EstablecimientoSerializer()

    class Meta:
        model = Ficha
        fields = '__all__'


class ServicioClinicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicioClinico
        fields = ('id', 'nombre')


class MovimientoFichaSerializer(serializers.ModelSerializer):
    ficha = FichaSerializer(read_only=True)
    servicio_clinico_envio = ServicioClinicoSerializer(read_only=True)
    servicio_clinico_recepcion = ServicioClinicoSerializer(read_only=True)

    class Meta:
        model = MovimientoFicha
        fields = '__all__'
        read_only_fields = (
            'fecha_envio', 'observacion_envio', 'estado_envio', 'servicio_clinico_envio', 'usuario_envio',
            'profesional_envio',
            'ficha', 'estado_recepcion', 'usuario_recepcion', 'fecha_recepcion', 'servicio_clinico_recepcion',
            'observacion_recepcion', 'profesional_recepcion'
        )


class RecepcionFichaViewSet(viewsets.ModelViewSet):
    serializer_class = MovimientoFichaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = MovimientoFicha.objects.select_related(
            'ficha__paciente',
            'ficha__establecimiento',
            'servicio_clinico_envio',
            'servicio_clinico_recepcion',
            'usuario_envio',
            'usuario_recepcion',
            'profesional_envio',
            'profesional_recepcion',
        ).filter(
            fecha_envio__isnull=False,
            estado_recepcion__in=['EN ESPERA', 'RECIBIDO'],
            ficha__establecimiento=user.establecimiento
        ).order_by('-updated_at')
        return qs

    @action(detail=True, methods=['post'], url_path='mark_received')
    def mark_received(self, request, pk=None):
        try:
            m = self.get_queryset().get(id=pk)
        except MovimientoFicha.DoesNotExist:
            return Response({'ok': False, 'error': 'No encontrado'}, status=status.HTTP_404_NOT_FOUND)

        if m.estado_recepcion == 'RECIBIDO':
            return Response({'ok': False, 'error': 'El movimiento ya fue recepcionado.'},
                            status=status.HTTP_400_BAD_REQUEST)

        fecha_recepcion = request.data.get('fecha_recepcion')
        obs = request.data.get('observacion_recepcion')
        profesional_id = request.data.get('profesional_recepcion')
        from datetime import datetime

        if fecha_recepcion:
            try:
                dt = datetime.fromisoformat(fecha_recepcion)
            except Exception:
                dt = timezone.now()
        else:
            dt = timezone.now()

        m.fecha_recepcion = dt
        if obs is not None:
            m.observacion_recepcion = obs
        if profesional_id:
            try:
                from kardex.models import Profesional
                m.profesional_recepcion = Profesional.objects.get(pk=profesional_id)
            except Exception:
                pass
        m.usuario_recepcion = request.user
        m.estado_recepcion = 'RECIBIDO'
        m.save()

        return Response({'ok': True, 'id': m.id})
