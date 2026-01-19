from django.urls import path

from clinica.apis.movimientos_ficha_paciente import get_movimientos_paciente_establecimiento
from clinica.views.pdf import pdf_stickers, pdf_index

urlpatterns = [
    # Movimientos de Fichas del Paciente
    path('api/movimientos/paciente/<str:rut>/', get_movimientos_paciente_establecimiento,
         name='api_movimientos_paciente_establecimiento'),

    path(
        "pdfs/stickers/ficha/<int:ficha_id>/", pdf_stickers, name="pdf_stickers_ficha"
    ),
    path(
        "pdfs/stickers/paciente/<int:paciente_id>/", pdf_stickers, name="pdf_stickers_paciente"
    ),

    path("pdfs/ficha/<int:ficha_id>/", pdf_index, name="pdf_ficha"),
    path("pdfs/ficha/paciente/<int:paciente_id>/", pdf_index, name="pdf_ficha_paciente"),
]
