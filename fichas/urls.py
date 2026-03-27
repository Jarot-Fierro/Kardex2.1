from django.urls import path

from .views import PacienteFichaManageView

urlpatterns = [
    path('paciente-ficha/', PacienteFichaManageView.as_view(), name='ficha_paciente_manage'),
]
