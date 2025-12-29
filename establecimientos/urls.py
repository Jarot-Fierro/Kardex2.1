from django.urls import path

from establecimientos.views.establecimiento import *
from establecimientos.views.sectores import *

urlpatterns = [

    # Vistas básicas para Establecimientos
    path('establecimientos/', EstablecimientoListView.as_view(), name='establecimiento_list'),
    path('establecimientos/crear/', EstablecimientoCreateView.as_view(), name='establecimiento_create'),
    path('establecimientos/<int:pk>/editar/', EstablecimientoUpdateView.as_view(), name='establecimiento_update'),
    path('establecimientos/<int:pk>/detalle/', EstablecimientoDetailView.as_view(), name='establecimiento_detail'),
    path('establecimientos/historial/', EstablecimientoHistoryListView.as_view(), name='establecimiento_history'),

    # Vistas básicas para Servicios Clínicos
    # path('servicios-clinicos/', ServicioClinicoListView.as_view(), name='servicio_clinico_list'),
    # path('servicios-clinicos/crear/', ServicioClinicoCreateView.as_view(), name='servicio_clinico_create'),
    # path('servicios-clinicos/<int:pk>/editar/', ServicioClinicoUpdateView.as_view(), name='servicio_clinico_update'),
    # path('servicios-clinicos/<int:pk>/detalle/', ServicioClinicoDetailView.as_view(), name='servicio_clinico_detail'),
    # path('servicios-clinicos/historial/', ServicioClinicoHistoryListView.as_view(), name='servicio_clinico_history'),

    # # Vistas para sectores
    path('sectores/', SectorListView.as_view(), name='sector_list'),
    path('sectores/nuevo/', SectorCreateView.as_view(), name='sector_create'),
    path('sectores/<int:pk>/', SectorDetailView.as_view(), name='sector_detail'),
    path('sectores/<int:pk>/editar/', SectorUpdateView.as_view(), name='sector_update'),
    path('sectores/historial/', SectorHistoryListView.as_view(), name='sector_history'),

]
