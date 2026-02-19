from django.urls import path

from clinica.apis.buscar_paciente import (
    buscar_paciente_ficha_api, buscar_paciente_recepcion_api, buscar_paciente_traspaso_api,
    buscar_paciente_ficha_api_monologo, buscar_paciente_recepcion_api_monologo
)
from clinica.apis.movimiento_ficha_monologo_controlado import RegistrarSalidaAPI, RegistrarRecepcionAPI
from clinica.apis.movimientos_ficha_paciente import get_movimientos_paciente_establecimiento
from clinica.views.fichas import *
from clinica.views.movimiento_ficha import *
from clinica.views.movimiento_ficha_monologo_controlado import SalidaFichaView, SalidaFichaUpdateView, \
    RecepcionFichaView, FichasEnTransitoView
from clinica.views.pdf import pdf_stickers, pdf_index, pdf_movimientos_fichas, \
    pdf_movimientos_fichas_monologo_controlado

urlpatterns = [
    path('fichas/', FichaListView.as_view(), name='ficha_list'),
    # path('fichas/crear/', FichaCreateView.as_view(), name='ficha_create'),
    path('fichas/<int:pk>/editar/', FichaUpdateView.as_view(), name='ficha_update'),
    path('fichas/<int:pk>/detalle/', FichaDetailView.as_view(), name='ficha_detail'),
    path('fichas/<int:pk>/toggle-pasivar/', TogglePasivadoFichaView.as_view(), name='ficha_toggle_pasivar'),
    path('fichas/<int:pk>/tarjeta/', FichaTarjetaView.as_view(), name='ficha_tarjeta'),
    path('fichas/pasivadas/', PacientePasivadosListView.as_view(), name='ficha_pasivados_list'),
    path('fichas/historial/', FichaHistoryListView.as_view(), name='ficha_history'),

    # Nuevas vistas de movimientos (Recepción y Salida)
    path('salida-ficha-masiva/', SalidaTablaFichaView.as_view(), name='salida_ficha_masiva'),
    path('entrada-tabla-ficha/', RecepcionTablaFichaView.as_view(), name='entrada_tabla_ficha'),
    path('traspaso-ficha/', TraspasoTablaFichaView.as_view(), name='traspaso_ficha'),
    path('fichas-en-transito/', FichasEnTransito.as_view(), name='fichas_en_transito'),

    # Movimientos de Fichas del Paciente
    path('api/movimientos/paciente/<str:rut>/', get_movimientos_paciente_establecimiento,
         name='api_movimientos_paciente_establecimiento'),

    # Movimiento Monologo Controlado
    path('movimientos-monologo/salida/', SalidaFichaView.as_view(), name='movimiento_monologo_salida'),
    path('movimientos-monologo/salida/<int:pk>/editar/', SalidaFichaUpdateView.as_view(),
         name='movimiento_monologo_salida_update'),
    path('movimientos-monologo/recepcion/', RecepcionFichaView.as_view(), name='movimiento_monologo_recepcion'),
    path('fichas-en-transito-controlado/', FichasEnTransitoView.as_view(), name='fichas_en_transito_monologo'),
    path('api/movimientos-fichas-monologo/salida/', RegistrarSalidaAPI.as_view(),
         name='api_movimiento_monologo_salida'),
    path('api/movimientos-fichas-monologo/recepcion/', RegistrarRecepcionAPI.as_view(),
         name='api_movimiento_monologo_recepcion'),

    path('api/ficha-paciente/buscar/', buscar_paciente_ficha_api, name='ficha-paciente-buscar'),
    path('api/ficha-paciente/buscar/monologo/', buscar_paciente_ficha_api_monologo,
         name='ficha-paciente-buscar-monologo'),

    path('api/ficha-paciente/buscar-recepcion/', buscar_paciente_recepcion_api, name='ficha-paciente-buscar-recepcion'),
    path('api/ficha-paciente/buscar-recepcion/monologo/', buscar_paciente_recepcion_api_monologo,
         name='ficha-paciente-buscar-recepcion-monologo'),

    path('api/ficha-paciente/buscar-traspaso/', buscar_paciente_traspaso_api, name='ficha-paciente-buscar-traspaso'),

    path(
        "pdfs/stickers/ficha/<int:ficha_id>/", pdf_stickers, name="pdf_stickers_ficha"
    ),
    path(
        "pdfs/stickers/paciente/<int:paciente_id>/", pdf_stickers, name="pdf_stickers_paciente"
    ),

    path("pdfs/ficha/<int:ficha_id>/", pdf_index, name="pdf_ficha"),
    path("pdfs/ficha/paciente/<int:paciente_id>/", pdf_index, name="pdf_ficha_paciente"),
    path("pdfs/movimientos/", pdf_movimientos_fichas, name="pdf_movimientos_fichas"),
    path("pdfs/movimientos-monologo/", pdf_movimientos_fichas_monologo_controlado,
         name="pdf_movimientos_fichas_monologo_controlado"),
]
