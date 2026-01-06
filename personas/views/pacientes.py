from django.shortcuts import render

from establecimientos.models.sectores import Sector
from geografia.models.comuna import Comuna
from personas.models.genero import Genero
from personas.models.prevision import Prevision


def paciente_view(request):
    generos = Genero.objects.filter(status=True)
    previsiones = Prevision.objects.filter(status=True)
    comunas = Comuna.objects.filter(status=True)
    sectores = Sector.objects.filter(status=True, establecimiento=request.user.establecimiento)
    return render(request, 'paciente/form.html',
                  context={
                      'generos': generos,
                      'previsiones': previsiones,
                      'comunas': comunas,
                      'sectores': sectores,
                      'title': 'Registro/Consulta de Paciente'
                  })
