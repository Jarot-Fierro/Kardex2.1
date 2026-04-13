from django.urls import path

from respaldos.views.respaldos_fichas import RespaldoFichasListView, RespaldoFichasDetailView
from respaldos.views.respaldos_movimientos import RespaldoMovimientosListView, RespaldoMovimientosDetailView
from respaldos.views.respaldos_pacientes import RespaldoPacientesListView, RespaldoPacientesDetailView

urlpatterns = [
    # Respaldos de Fichas
    path('fichas/', RespaldoFichasListView.as_view(), name='respaldo_fichas_list'),
    path('fichas/detalle/<int:pk>/', RespaldoFichasDetailView.as_view(), name='respaldo_fichas_detail'),

    # Respaldos de Movimientos
    path('movimientos/', RespaldoMovimientosListView.as_view(), name='respaldo_movimientos_list'),
    path('movimientos/detalle/<int:pk>/', RespaldoMovimientosDetailView.as_view(), name='respaldo_movimientos_detail'),

    # Respaldos de Pacientes
    path('pacientes/', RespaldoPacientesListView.as_view(), name='respaldo_pacientes_list'),
    path('pacientes/detalle/<int:pk>/', RespaldoPacientesDetailView.as_view(), name='respaldo_pacientes_detail'),
]
