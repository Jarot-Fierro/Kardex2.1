from rest_framework import viewsets, filters, serializers
from rest_framework.permissions import IsAuthenticated

from kardex.models import ServicioClinico, Profesional


class ServicioClinicoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServicioClinico.objects.filter(status='ACTIVE').order_by('nombre')
    permission_classes = [IsAuthenticated]

    class SerializerClass:
        pass

    class Serializer(serializers.ModelSerializer):
        class Meta:
            model = ServicioClinico
            fields = ('id', 'nombre')

    serializer_class = Serializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre']


class ProfesionalViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    class Serializer(serializers.ModelSerializer):
        class Meta:
            model = Profesional
            fields = ('id', 'nombres', 'apellido_paterno', 'apellido_materno', 'establecimiento_id')

    serializer_class = Serializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombres', 'apellido_paterno', 'apellido_materno', 'rut']

    def get_queryset(self):
        qs = Profesional.objects.filter(status='ACTIVE').order_by('nombres', 'apellido_paterno')
        # Filtrar por establecimiento del usuario si existe
        user = getattr(self.request, 'user', None)
        est = getattr(user, 'establecimiento', None)
        if est:
            qs = qs.filter(establecimiento=est)
        return qs
