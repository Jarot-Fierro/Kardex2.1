from django.shortcuts import render
from django.urls import path

from establecimientos.views.establecimiento import *
from establecimientos.views.sectores import *
from establecimientos.views.servicio_clinico import *
from geografia.views.comuna import *
from kardex.views.api.paciente_ficha import PacienteFichaViewSet
from kardex.views.contacto import ContactoView
from kardex.views.ficha import *
from kardex.views.movimiento_fichas import *
from kardex.views.movimiento_fichas_update import SalidaFicha2View, SalidaTablaFichaView, RecepcionTablaFichaView
from kardex.views.pdfs import pdf_index, pdf_stickers
from kardex.views.soporte import TicketCreateView, SoporteListView
from kardex.views.tutoriales import TutorialesView
from personas.views.pacientes import *
from personas.views.prevision import *
from personas.views.profesion import *
from personas.views.profesionales import *

app_name = 'kardex'

urlpatterns = [
    # Vistas básicas para Paises

    # Vistas básicas para Comunas
    path('comunas/', ComunaListView.as_view(), name='comuna_list'),
    path('comunas/crear/', ComunaCreateView.as_view(), name='comuna_create'),
    path('comunas/<int:pk>/editar/', ComunaUpdateView.as_view(), name='comuna_update'),
    path('comunas/<int:pk>/detalle/', ComunaDetailView.as_view(), name='comuna_detail'),
    path('comunas/historial/', ComunaHistoryListView.as_view(), name='comuna_history'),

    # Vistas básicas para Establecimientos
    path('establecimientos/', EstablecimientoListView.as_view(), name='establecimiento_list'),
    path('establecimientos/crear/', EstablecimientoCreateView.as_view(), name='establecimiento_create'),
    path('establecimientos/<int:pk>/editar/', EstablecimientoUpdateView.as_view(), name='establecimiento_update'),
    path('establecimientos/<int:pk>/detalle/', EstablecimientoDetailView.as_view(), name='establecimiento_detail'),
    path('establecimientos/historial/', EstablecimientoHistoryListView.as_view(), name='establecimiento_history'),

    # Vistas básicas para Profesiones
    path('profesiones/', ProfesionListView.as_view(), name='profesion_list'),
    path('profesiones/crear/', ProfesionCreateView.as_view(), name='profesion_create'),
    path('profesiones/<int:pk>/editar/', ProfesionUpdateView.as_view(), name='profesion_update'),
    path('profesiones/<int:pk>/detalle/', ProfesionDetailView.as_view(), name='profesion_detail'),
    path('profesiones/historial/', ProfesionalHistoryListView.as_view(), name='profesion_history'),

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

    # Vistas básicas para Pacientes
    path('pacientes/', PacienteListView.as_view(), name='paciente_list'),
    path('pacientes/recien-nacidos/', PacienteRecienNacidoListView.as_view(), name='paciente_recien_nacido_list'),
    path('pacientes/extranjeros/', PacienteExtranjeroListView.as_view(), name='paciente_extranjero_list'),
    path('pacientes/rut-madre-reponsable/', PacienteRutMadreListView.as_view(), name='paciente_rut_madre_list'),
    path('pacientes/fallecidos/', PacienteFallecidoListView.as_view(), name='paciente_fallecido_list'),
    path('pacientes/por-fecha/', PacientePorFechaListView.as_view(), name='paciente_por_fecha_list'),
    path('pacientes/por-fecha/form/', PacienteFechaFormView.as_view(), name='paciente_fecha_form'),
    path('pacientes/<int:pk>/detalle/', PacienteDetailView.as_view(), name='paciente_detail'),
    path('consulta-pacientes/', PacienteQueryView.as_view(), name='paciente_query'),
    path('pacientes/<int:pk>/actualizar-rut/', PacienteActualizarRut.as_view(), name='paciente_actualizar_rut'),
    path('pacientes/crear/sin-rut/', PacienteCreateSinRutView.as_view(), name='paciente_create_sin_rut'),
    path('pacientes-pueblo_indigena/', PacientePuebloIndigenaListView.as_view(), name='paciente_pueblo_indigena_list'),
    path('pacientes/historial', PacientesHistoryListView.as_view(), name='paciente_history'),

    # Vistas básicas para Fichas
    path('fichas/', FichaListView.as_view(), name='ficha_list'),
    path('fichas/crear/', FichaCreateView.as_view(), name='ficha_create'),
    path('fichas/<int:pk>/editar/', FichaUpdateView.as_view(), name='ficha_update'),
    path('fichas/<int:pk>/detalle/', FichaDetailView.as_view(), name='ficha_detail'),
    path('fichas/<int:pk>/toggle-pasivar/', TogglePasivadoFichaView.as_view(), name='ficha_toggle_pasivar'),
    path('fichas/<int:pk>/tarjeta/', FichaTarjetaView.as_view(), name='ficha_tarjeta'),
    path('fichas/pasivadas/', PacientePasivadosListView.as_view(), name='ficha_pasivados_list'),
    path('fichas/historial/', FichaHistoryListView.as_view(), name='ficha_history'),

    # Vistas básicas para Movimientos de Ficha
    path('movimientos-ficha/', MovimientoFichaListView.as_view(), name='movimiento_ficha_list'),
    path('movimientos-ficha/crear/', MovimientoFichaCreateView.as_view(), name='movimiento_ficha_create'),
    path('movimientos-ficha/<int:pk>/editar/', MovimientoFichaUpdateView.as_view(), name='movimiento_ficha_update'),
    path('movimientos-ficha/<int:pk>/detalle/', MovimientoFichaDetailView.as_view(), name='movimiento_ficha_detail'),
    path('movimientos-ficha/historial/', MovimientosFichasHistoryListView.as_view(), name='movimiento_ficha_history'),

    # Vistas básicas para Servicios Clínicos
    path('servicios-clinicos/', ServicioClinicoListView.as_view(), name='servicio_clinico_list'),
    path('servicios-clinicos/crear/', ServicioClinicoCreateView.as_view(), name='servicio_clinico_create'),
    path('servicios-clinicos/<int:pk>/editar/', ServicioClinicoUpdateView.as_view(), name='servicio_clinico_update'),
    path('servicios-clinicos/<int:pk>/detalle/', ServicioClinicoDetailView.as_view(), name='servicio_clinico_detail'),
    path('servicios-clinicos/historial/', ServicioClinicoHistoryListView.as_view(), name='servicio_clinico_history'),

    # Vistas para sectores
    path('sectores/', SectorListView.as_view(), name='sector_list'),
    path('sectores/nuevo/', SectorCreateView.as_view(), name='sector_create'),
    path('sectores/<int:pk>/', SectorDetailView.as_view(), name='sector_detail'),
    path('sectores/<int:pk>/editar/', SectorUpdateView.as_view(), name='sector_update'),
    path('sectores/historial/', SectorHistoryListView.as_view(), name='sector_history'),

    path('pdf/', pdf_index, name='pdf_prueba'),
    path('pdfs/paciente/<int:paciente_id>/', pdf_index, name='pdf_paciente'),
    path('pdfs/ficha/<int:ficha_id>/', pdf_index, name='pdf_ficha'),

    path('pdfs/sticker/paciente/<int:paciente_id>/', pdf_stickers, name='pdf_stickers'),
    path('pdfs/stickers/ficha/<int:ficha_id>/', pdf_stickers, name='pdf_stickers_ficha'),

    # Nuevas vistas de movimientos (Recepción y Salida)
    path('movimientos/recepcion/', RecepcionFichaView.as_view(), name='recepcion_ficha'),
    path('movimientos/salida/', SalidaFichaView.as_view(), name='salida_ficha'),
    path('movimientos/traspaso/', TraspasoFichaView.as_view(), name='traspaso_ficha'),
    path('movimientos/transito/', MovimientoFichaTransitoListView.as_view(), name='movimiento_ficha_transito'),

    path('api/api_pacientes/', PacienteFichaViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='api_pacientes'),

    path('api/api_pacientes/<int:pk>/', PacienteFichaViewSet.as_view({
        'put': 'update'
    }), name='api_paciente_update'),

    path('salida-ficha-masiva/', SalidaFicha2View.as_view(), name='salida_ficha_masiva'),
    path('salida-tabla-ficha/', SalidaTablaFichaView.as_view(), name='salida_tabla_ficha'),
    path('entrada-tabla-ficha/', RecepcionTablaFichaView.as_view(), name='entrada_tabla_ficha'),

    #     Soporte
    path('contacto/', ContactoView.as_view(), name='contacto'),
    path('tickets/nuevo/', TicketCreateView.as_view(), name='ticket_create'),
    path('ticket/listado/', SoporteListView.as_view(), name='ticket_listado'),

    path('tutoriales/', TutorialesView.as_view(), name='tutoriales'),

]


def custom_permission_denied_view(request, exception):
    return render(request, '403.html', status=403)


def custom_page_not_found_view(request, exception):
    return render(request, '404.html', status=404)


handler403 = custom_permission_denied_view
handler404 = custom_page_not_found_view
