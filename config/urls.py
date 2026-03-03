from django.contrib import admin
from django.db.models import Count
from django.http import JsonResponse
from django.urls import path, include

from clinica.models import MovimientoMonologoControlado
from core.views import *


def debug_integridad_view(request):
    # =========================
    # 1️⃣ Pacientes con RUT duplicado
    # =========================
    pacientes_duplicados_qs = (
        Paciente.objects
        .values('rut')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
    )

    pacientes_duplicados = []
    for item in pacientes_duplicados_qs:
        rut = item['rut']
        ids = list(
            Paciente.objects
            .filter(rut=rut)
            .values_list('id', flat=True)
        )
        pacientes_duplicados.append({
            'rut': rut,
            'ids': ids
        })

    # =========================
    # 2️⃣ Fichas duplicadas por establecimiento
    # =========================
    fichas_duplicadas_qs = (
        Ficha.objects
        .values('numero_ficha_sistema', 'establecimiento_id')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
    )

    fichas_duplicadas = []
    for item in fichas_duplicadas_qs:
        numero = item['numero_ficha_sistema']
        establecimiento_id = item['establecimiento_id']

        ids = list(
            Ficha.objects
            .filter(
                numero_ficha_sistema=numero,
                establecimiento_id=establecimiento_id
            )
            .values_list('id', flat=True)
        )

        fichas_duplicadas.append({
            'numero_ficha_sistema': numero,
            'establecimiento_id': establecimiento_id,
            'ids': ids
        })

    # =========================
    # 3️⃣ Movimientos sin ficha
    # =========================
    movimientos_sin_ficha = list(
        MovimientoMonologoControlado.objects
        .filter(ficha__isnull=True)
        .values_list('id', flat=True)
    )

    # =========================
    # 4️⃣ Movimientos con ficha pero sin paciente
    # =========================
    movimientos_sin_paciente = list(
        MovimientoMonologoControlado.objects
        .filter(
            ficha__isnull=False,
            ficha__paciente__isnull=True
        )
        .values_list('id', flat=True)
    )

    return JsonResponse({
        'pacientes_duplicados': pacientes_duplicados,
        'fichas_duplicadas': fichas_duplicadas,
        'movimientos_sin_ficha': movimientos_sin_ficha,
        'movimientos_sin_paciente': movimientos_sin_paciente,
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
