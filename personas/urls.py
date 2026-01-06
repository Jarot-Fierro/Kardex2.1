from django.urls import path

from personas.apis.ficha_paciente import get_paciente_ficha
from personas.views.genero import *
from personas.views.pacientes import paciente_view
from personas.views.prevision import *
from personas.views.profesion import *
from personas.views.profesionales import *

urlpatterns = [
    # Vistas básicas para Profesiones
    path('profesiones/', ProfesionListView.as_view(), name='profesion_list'),
    path('profesiones/crear/', ProfesionCreateView.as_view(), name='profesion_create'),
    path('profesiones/<int:pk>/editar/', ProfesionUpdateView.as_view(), name='profesion_update'),
    path('profesiones/<int:pk>/detalle/', ProfesionDetailView.as_view(), name='profesion_detail'),
    path('profesiones/historial/', ProfesionHistoryListView.as_view(), name='profesion_history'),

    # Vistas básicas para Profesionales
    path('profesionales/', ProfesionalListView.as_view(), name='profesional_list'),
    path('profesionales/crear/', ProfesionalCreateView.as_view(), name='profesional_create'),
    path('profesionales/<int:pk>/editar/', ProfesionalUpdateView.as_view(), name='profesional_update'),
    path('profesionales/<int:pk>/detalle/', ProfesionalDetailView.as_view(), name='profesional_detail'),
    path('profesionales/history/', ProfesionalHistoryListView.as_view(), name='profesional_history'),

    # Vistas básicas para Prevision
    path('prevision/', PrevisionListView.as_view(), name='prevision_list'),
    path('prevision/crear/', PrevisionCreateView.as_view(), name='prevision_create'),
    path('prevision/<int:pk>/editar/', PrevisionUpdateView.as_view(), name='prevision_update'),
    path('prevision/<int:pk>/detalle/', PrevisionDetailView.as_view(), name='prevision_detail'),
    path('prevision/historial', PrevisionHistoryListView.as_view(), name='prevision_history'),

    # Vistas básicas para Género
    path('genero/', GeneroListView.as_view(), name='genero_list'),
    path('genero/crear/', GeneroCreateView.as_view(), name='genero_create'),
    path('genero/<int:pk>/editar/', GeneroUpdateView.as_view(), name='genero_update'),
    path('genero/<int:pk>/detalle/', GeneroDetailView.as_view(), name='genero_detail'),
    path('genero/historial', GeneroHistoryListView.as_view(), name='genero_history'),

    # Vistas básicas para Pacientes
    # path('pacientes/', PacienteListView.as_view(), name='paciente_list'),
    # path('pacientes/recien-nacidos/', PacienteRecienNacidoListView.as_view(), name='paciente_recien_nacido_list'),
    # path('pacientes/extranjeros/', PacienteExtranjeroListView.as_view(), name='paciente_extranjero_list'),
    # path('pacientes/rut-madre-reponsable/', PacienteRutMadreListView.as_view(), name='paciente_rut_madre_list'),
    # path('pacientes/fallecidos/', PacienteFallecidoListView.as_view(), name='paciente_fallecido_list'),
    # path('pacientes/por-fecha/', PacientePorFechaListView.as_view(), name='paciente_por_fecha_list'),
    # path('pacientes/por-fecha/form/', PacienteFechaFormView.as_view(), name='paciente_fecha_form'),
    # path('pacientes/<int:pk>/detalle/', PacienteDetailView.as_view(), name='paciente_detail'),
    # path('consulta-pacientes/', PacienteQueryView.as_view(), name='paciente_query'),
    # path('pacientes/<int:pk>/actualizar-rut/', PacienteActualizarRut.as_view(), name='paciente_actualizar_rut'),
    # path('pacientes/crear/sin-rut/', PacienteCreateSinRutView.as_view(), name='paciente_create_sin_rut'),
    # path('pacientes-pueblo_indigena/', PacientePuebloIndigenaListView.as_view(), name='paciente_pueblo_indigena_list'),
    # path('pacientes/historial', PacientesHistoryListView.as_view(), name='paciente_history'),

    # APIS
    path("ficha-paciente/<str:rut>/", get_paciente_ficha, name="get_paciente_ficha", ),
    path("paciente/", paciente_view, name="paciente_view", ),

]
