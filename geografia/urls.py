from django.urls import path

from geografia.views.comuna import *
from geografia.views.pais import *

urlpatterns = [
    path('lista-comunas/', ComunaListView.as_view(), name='list_comunas'),
    path('detalle-comunas/<int:pk>/detalle/', ComunaDetailView.as_view(), name='detail_comunas'),
    path('crear-comunas/', ComunaCreateView.as_view(), name='create_comunas'),
    path('actualizar-comunas/<int:pk>/detalle/', ComunaUpdateView.as_view(), name='update_comunas'),
    path('historial-comunas/', ComunaHistoryListView.as_view(), name='historical_comunas'),

    path('paises/', PaisListView.as_view(), name='pais_list'),
    path('paises/crear/', PaisCreateView.as_view(), name='pais_create'),
    path('paises/<int:pk>/editar/', PaisUpdateView.as_view(), name='pais_update'),
    path('paises/<int:pk>/detalle/', PaisDetailView.as_view(), name='pais_detail'),
    path('paises/historial/', PaisHistoryListView.as_view(), name='pais_history'),
]
