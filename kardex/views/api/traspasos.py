from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated

from kardex.models import MovimientoFicha, Ficha, Paciente, Establecimiento, ServicioClinico, Profesional


class EstablecimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Establecimiento
        fields = ('id', 'nombre')


class PacienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = ('id', 'rut', 'nombre', 'apellido_paterno', 'apellido_materno')


class ServicioClinicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicioClinico
        fields = ('id', 'nombre')


class ProfesionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profesional
        fields = ('id', 'nombres')


class FichaSerializer(serializers.ModelSerializer):
    paciente = PacienteSerializer(read_only=True)
    establecimiento = EstablecimientoSerializer(read_only=True)

    class Meta:
        model = Ficha
        fields = ('id', 'numero_ficha_sistema', 'paciente', 'establecimiento')


class MovimientoFichaSerializer(serializers.ModelSerializer):
    ficha = FichaSerializer(read_only=True)
    servicio_clinico_envio = ServicioClinicoSerializer(read_only=True)
    servicio_clinico_recepcion = ServicioClinicoSerializer(read_only=True)
    servicio_clinico_traspaso = ServicioClinicoSerializer(read_only=True)
    profesional_envio = ProfesionalSerializer(read_only=True)
    profesional_recepcion = ProfesionalSerializer(read_only=True)
    profesional_traspaso = ProfesionalSerializer(read_only=True)

    class Meta:
        model = MovimientoFicha
        fields = '__all__'


class TraspasoFichaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API de solo lectura para consultar movimientos de fichas con foco en traspasos.
    Filtra por establecimiento del usuario autenticado y permite búsqueda por RUT o N° de ficha.
    """
    serializer_class = MovimientoFichaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = (
            MovimientoFicha.objects.select_related(
                'ficha__paciente',
                'ficha__establecimiento',
                'servicio_clinico_envio',
                'servicio_clinico_recepcion',
                'servicio_clinico_traspaso',
                'profesional_envio',
                'profesional_recepcion',
                'profesional_traspaso',
            )
            .filter(ficha__establecimiento=user.establecimiento)
            .order_by('-fecha_envio', '-created_at')
        )

        term = (self.request.query_params.get('search') or '').strip()
        if term:
            from django.db.models import Q
            qs = qs.filter(
                Q(ficha__paciente__rut__icontains=term)
                | Q(ficha__numero_ficha_sistema__icontains=term)
            )
        return qs
