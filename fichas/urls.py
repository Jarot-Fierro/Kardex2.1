from django.urls import path

from .views import PacienteFichaManageView, PacienteAutocompleteView, FusionarPacientesView

urlpatterns = [
    path('paciente-ficha/', PacienteFichaManageView.as_view(), name='ficha_paciente_manage'),
    path('paciente-autocomplete/', PacienteAutocompleteView.as_view(), name='paciente_autocomplete'),
    path('fusionar-pacientes/', FusionarPacientesView.as_view(), name='fusionar_pacientes'),
]
