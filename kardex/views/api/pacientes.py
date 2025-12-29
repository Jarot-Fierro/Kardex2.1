from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework import viewsets, filters

from kardex.models import Paciente


class PacienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = '__all__'


class PacienteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PacienteSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    # Permitir búsqueda por múltiples campos comunes de identificación
    search_fields = ['rut', 'codigo', 'nombre', 'apellido_paterno', 'apellido_materno']
    queryset = Paciente.objects.all()

    def get_queryset(self):
        # Se deja que SearchFilter maneje el parámetro ?search=...
        # Solo definimos un orden por defecto estable.
        return Paciente.objects.all().order_by('-id')
