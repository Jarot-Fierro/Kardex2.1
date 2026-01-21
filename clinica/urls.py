from django.urls import path

from clinica.apis.buscar_paciente import (
    buscar_paciente_ficha_api, buscar_paciente_recepcion_api, buscar_paciente_traspaso_api
)
from clinica.apis.movimientos_ficha_paciente import get_movimientos_paciente_establecimiento
from clinica.views.fichas import *
from clinica.views.movimiento_ficha import *
from clinica.views.pdf import pdf_stickers, pdf_index

urlpatterns = [
    path('fichas/', FichaListView.as_view(), name='ficha_list'),
    path('fichas/crear/', FichaCreateView.as_view(), name='ficha_create'),
    path('fichas/<int:pk>/editar/', FichaUpdateView.as_view(), name='ficha_update'),
    path('fichas/<int:pk>/detalle/', FichaDetailView.as_view(), name='ficha_detail'),
    path('fichas/<int:pk>/toggle-pasivar/', TogglePasivadoFichaView.as_view(), name='ficha_toggle_pasivar'),
    path('fichas/<int:pk>/tarjeta/', FichaTarjetaView.as_view(), name='ficha_tarjeta'),
    path('fichas/pasivadas/', PacientePasivadosListView.as_view(), name='ficha_pasivados_list'),
    path('fichas/historial/', FichaHistoryListView.as_view(), name='ficha_history'),

    # Nuevas vistas de movimientos (Recepción y Salida)
    path('salida-ficha-masiva/', SalidaFicha2View.as_view(), name='salida_ficha_masiva'),
    path('salida-tabla-ficha/', SalidaTablaFichaView.as_view(), name='salida_tabla_ficha'),
    path('entrada-tabla-ficha/', RecepcionTablaFichaView.as_view(), name='entrada_tabla_ficha'),
    path('traspaso-ficha/', TraspasoFichaView.as_view(), name='traspaso_ficha'),

    # Movimientos de Fichas del Paciente
    path('api/movimientos/paciente/<str:rut>/', get_movimientos_paciente_establecimiento,
         name='api_movimientos_paciente_establecimiento'),

    path('api/ficha-paciente/buscar/', buscar_paciente_ficha_api, name='ficha-paciente-buscar'),
    path('api/ficha-paciente/buscar-recepcion/', buscar_paciente_recepcion_api, name='ficha-paciente-buscar-recepcion'),
    path('api/ficha-paciente/buscar-traspaso/', buscar_paciente_traspaso_api, name='ficha-paciente-buscar-traspaso'),

    path(
        "pdfs/stickers/ficha/<int:ficha_id>/", pdf_stickers, name="pdf_stickers_ficha"
    ),
    path(
        "pdfs/stickers/paciente/<int:paciente_id>/", pdf_stickers, name="pdf_stickers_paciente"
    ),

    path("pdfs/ficha/<int:ficha_id>/", pdf_index, name="pdf_ficha"),
    path("pdfs/ficha/paciente/<int:paciente_id>/", pdf_index, name="pdf_ficha_paciente"),
]
