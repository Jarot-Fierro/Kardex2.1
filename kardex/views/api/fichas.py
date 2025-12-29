from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.contrib import messages

from kardex.models import Ficha
from kardex.models import Paciente, Establecimiento


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


class FichaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FichaSerializer
    filter_backends = [DjangoFilterBackend]
    queryset = Ficha.objects.none()

    def get_queryset(self):
        user = self.request.user
        search_term = self.request.query_params.get('search', '').strip()
        tipo_busqueda = self.request.query_params.get('tipo', '').strip()

        queryset = (
            Ficha.objects
            .select_related('paciente', 'establecimiento', 'usuario', 'profesional')
            .filter(establecimiento=user.establecimiento)
            .order_by('id')
        )

        if search_term:
            if tipo_busqueda == 'rut':
                queryset = queryset.filter(paciente__rut__icontains=search_term)
            elif tipo_busqueda == 'codigo':
                queryset = queryset.filter(paciente__codigo__icontains=search_term)
            elif tipo_busqueda == 'ficha':
                try:
                    num = int(search_term)
                    queryset = queryset.filter(numero_ficha_sistema=num)
                except ValueError:
                    queryset = queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Si hay resultados, mantener comportamiento actual
        results = response.data
        # DRF puede envolver en {'count':...,'results':...}
        items = []
        if isinstance(results, dict) and 'results' in results:
            items = results.get('results') or []
        elif isinstance(results, list):
            items = results

        if items:
            return response

        # No hay fichas para el criterio; evaluar casos especiales de RUT
        search_term = request.query_params.get('search', '').strip()
        tipo_busqueda = request.query_params.get('tipo', '').strip()
        user = request.user
        establecimiento = getattr(user, 'establecimiento', None)

        if tipo_busqueda == 'rut' and search_term:
            paciente = Paciente.objects.filter(rut__iexact=search_term).first()
            if not paciente:
                return Response({
                    'status': 'not_found',
                    'message': 'Paciente no encontrado'
                }, status=status.HTTP_404_NOT_FOUND)

            # Paciente existe pero no tiene ficha en este establecimiento
            est_nombre = getattr(establecimiento, 'nombre', 'su establecimiento')
            return Response({
                'status': 'missing_ficha',
                'message': f'El paciente con el RUT {search_term} no tiene ficha existente en este establecimiento {est_nombre}',
                'confirm_text': f'¿Quiere agregar este paciente {search_term} con una ficha generada por el sistema al establecimiento {est_nombre}?',
                'paciente': {
                    'id': paciente.id,
                    'rut': paciente.rut,
                    'nombre': paciente.nombre,
                    'apellido_paterno': paciente.apellido_paterno,
                    'apellido_materno': paciente.apellido_materno,
                    'codigo': paciente.codigo,
                },
                'establecimiento': {
                    'id': getattr(establecimiento, 'id', None),
                    'nombre': est_nombre,
                },
                'create_url': request.build_absolute_uri('auto-create/')
            })

        # Si no aplica, devolver la respuesta vacía estándar
        return response

    @action(detail=False, methods=['post'], url_path='auto-create')
    def auto_create(self, request, *args, **kwargs):
        user = request.user
        establecimiento = getattr(user, 'establecimiento', None)
        if not establecimiento:
            return Response({'detail': 'El usuario no tiene un establecimiento asociado.'}, status=status.HTTP_400_BAD_REQUEST)

        rut = (request.data.get('rut') or '').strip()
        paciente_id = request.data.get('paciente_id')

        paciente = None
        if paciente_id:
            try:
                paciente = Paciente.objects.get(pk=paciente_id)
            except Paciente.DoesNotExist:
                return Response({'detail': 'Paciente no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        elif rut:
            paciente = Paciente.objects.filter(rut__iexact=rut).first()
            if not paciente:
                return Response({'detail': 'Paciente no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({'detail': 'Debe indicar rut o paciente_id'}, status=status.HTTP_400_BAD_REQUEST)

        # Si ya existe ficha en el establecimiento, no crear de nuevo
        if Ficha.objects.filter(paciente=paciente, establecimiento=establecimiento).exists():
            return Response({'detail': 'Ya existe una ficha para este paciente en su establecimiento.'}, status=status.HTTP_409_CONFLICT)

        ficha = Ficha.objects.create(
            paciente=paciente,
            usuario=user,
            establecimiento=establecimiento,
        )

        redirect_url = request.build_absolute_uri(
            reverse('kardex:paciente_query') + f'?paciente_id={paciente.id}'
        )

        return Response({
            'status': 'created',
            'ficha_id': ficha.id,
            'numero_ficha_sistema': ficha.numero_ficha_sistema,
            'paciente_id': paciente.id,
            'redirect_url': redirect_url,
        }, status=status.HTTP_201_CREATED)
