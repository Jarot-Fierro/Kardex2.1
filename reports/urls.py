from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    # MANTENEDORES
    path('export/pais/', views.export_pais, name='export_pais'),
    path('export/comuna/', views.export_comuna, name='export_comuna'),
    path('export/establecimiento/', views.export_establecimiento, name='export_establecimiento'),
    path('export/prevision/', views.export_prevision, name='export_prevision'),
    path('export/profesion/', views.export_profesion, name='export_profesion'),
    path('export/profesional/', views.export_profesional, name='export_profesional'),
    path('export/sector/', views.export_sector, name='export_sector'),
    path('export/servicio_clinico/', views.export_servicio_clinico, name='export_servicio_clinico'),

    # FICHAS
    path('export/ficha/', views.export_ficha_csv, name='export_ficha'),
    path('export/ficha_pasivada/', views.export_ficha_pasivadas_csv, name='export_ficha_pasivada'),

    # MOVIMIENTOS FICHAS
    path('export/movimiento_ficha/csv/', views.export_movimiento_ficha_csv, name='export_movimiento_ficha_csv'),
    path('export/movimiento_ficha_envio/csv/', views.export_movimiento_ficha_envio_csv,
         name='export_movimiento_ficha_envio_csv'),
    path('export/movimiento_ficha_recepcion/csv/', views.export_movimiento_ficha_recepcion_csv,
         name='export_movimiento_ficha_recepcion_csv'),
    path('export/movimiento_ficha_traspaso/csv/', views.export_movimiento_ficha_traspaso_csv,
         name='export_movimiento_ficha_traspaso_csv'),

    # === PACIENTES (EXPORTACIÓN CSV) ===
    path('export/paciente-csv/', views.export_paciente_csv, name='export_paciente_csv'),
    path('export/paciente_recien_nacido-csv/', views.export_paciente_recien_nacido_csv,
         name='export_paciente_recien_nacido_csv'),
    path('export/paciente_extranjero-csv/', views.export_paciente_extranjero_csv,
         name='export_paciente_extranjero_csv'),
    path('export/paciente_fallecido-csv/', views.export_paciente_fallecido_csv,
         name='export_paciente_fallecido_csv'),
    path('export/paciente_pueblo_indigena-csv/', views.export_paciente_pueblo_indigena_csv,
         name='export_paciente_pueblo_indigena_csv'),

]
