from django.db.models import Q
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from kardex.models.paciente_ficha import VistaFichaPaciente


class FichaPacienteSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = VistaFichaPaciente
        fields = [
            'paciente_id',
            'ficha_id',
            'rut',
            'numero_ficha_sistema',
            'nombre_completo'
        ]

    def get_nombre_completo(self, obj):
        """Concatenar nombre + apellido paterno + apellido materno"""
        nombre = obj.nombre or ''
        ap_paterno = obj.apellido_paterno or ''
        ap_materno = obj.apellido_materno or ''
        return f"{nombre} {ap_paterno} {ap_materno}".strip()


class FichaPacienteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para buscar pacientes por RUT o número de ficha.
    Solo entrega fichas del establecimiento del usuario autenticado.
    """
    serializer_class = FichaPacienteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtra SOLO por establecimiento del usuario autenticado"""
        user = self.request.user
        if not user or not hasattr(user, 'establecimiento') or not user.establecimiento:
            return VistaFichaPaciente.objects.none()
        # Principal: solo filtrar por establecimiento aquí; la búsqueda se maneja en la acción "buscar"
        return VistaFichaPaciente.objects.filter(establecimiento_id=user.establecimiento.id)

    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """
        Endpoint especializado para búsqueda por RUT (parcial o completo) y número de ficha exacto.
        URL: /api/fichas/buscar/?q=valor
        Sin paginación. Máximo 10 resultados.
        """
        base_qs = self.get_queryset()
        # Leer parámetro 'q'
        q = request.query_params.get('q', '')
        q = (q or '').strip()

        # Si no hay término, retornar vacío rápidamente (no exponemos all)
        if not q:
            return Response([])

        # Construir queryset según reglas
        qs = base_qs
        if q.isdigit():
            # Número: buscar RUT que contenga esos dígitos y número de ficha exacto
            qs = qs.filter(Q(rut__contains=q) | Q(numero_ficha_sistema=int(q)))
        else:
            # Texto: buscar por RUT parcial/icomtains (permite con puntos/guión)
            qs = qs.filter(rut__icontains=q)

        # Limitar a 10 resultados y evitar paginación devolviendo lista simple
        qs = qs.order_by('paciente_id')[:10]
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
