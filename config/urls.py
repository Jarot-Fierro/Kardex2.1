from django.contrib import admin
from django.db.models import Count
from django.http import JsonResponse
from django.urls import path, include

from clinica.models import Ficha
from core.views import *


def debug_integridad_view(request):
    # 1️⃣ Buscar combinaciones duplicadas
    duplicados = (
        Ficha.objects
        .values('numero_ficha_sistema', 'establecimiento_id')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
    )

    # 2️⃣ Obtener las fichas que coinciden con esas combinaciones
    fichas = Ficha.objects.filter(
        numero_ficha_sistema__in=[
            d['numero_ficha_sistema'] for d in duplicados
        ],
        establecimiento_id__in=[
            d['establecimiento_id'] for d in duplicados
        ]
    ).values(
        'id',
        'numero_ficha_sistema',
        'establecimiento_id',
        'paciente_id'
    )

    return JsonResponse({
        'total_grupos_duplicados': duplicados.count(),
        'fichas_duplicadas': list(fichas),
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('', dashboard_view, name='home'),
    path('inicio/', include('core.urls')),
    path('geografia/', include('geografia.urls')),
    path('establecimientos/', include('establecimientos.urls')),
    path('personas/', include('personas.urls')),
    path('clinica/', include('clinica.urls')),
    path('reportes/', include('reports.urls')),
    path('duplicados/', debug_integridad_view, name='debug_integridad'),
    path('mantenimiento/', maintenance_view, name='maintenance'),
]
