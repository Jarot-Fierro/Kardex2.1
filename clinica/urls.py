from django.urls import path

from clinica.apis.movimientos_ficha_paciente import get_movimientos_paciente_establecimiento

urlpatterns = [
    # Movimientos de Fichas del Paciente
    path('api/movimientos/paciente/<str:rut>/', get_movimientos_paciente_establecimiento,
         name='api_movimientos_paciente_establecimiento'),
]
