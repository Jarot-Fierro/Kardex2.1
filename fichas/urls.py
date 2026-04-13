from django.urls import path

from .views import PacienteFichaManageView, PacienteAutocompleteView, FusionarPacientesView, paciente_list_v2

urlpatterns = [
    path('paciente-ficha/', PacienteFichaManageView.as_view(), name='ficha_paciente_manage'),
    path('paciente-autocomplete/', PacienteAutocompleteView.as_view(), name='paciente_autocomplete'),
    path('fusionar-pacientes/', FusionarPacientesView.as_view(), name='fusionar_pacientes'),
    path('paciente-list-v2/', paciente_list_v2, name='paciente_list_v2'),
]
