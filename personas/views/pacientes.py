from datetime import datetime

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from clinica.forms.ficha import FichaForm
from clinica.models import Ficha
from personas.forms.pacientes import PacienteForm
from personas.models.pacientes import Paciente


def capturar_datos_paciente(request):
    return {
        "paciente_id": request.POST.get('paciente_id'),
        "rut": request.POST.get('rut'),
        "nombre": request.POST.get('nombre'),
        "apellido_paterno": request.POST.get('apellido_paterno'),
        "apellido_materno": request.POST.get('apellido_materno'),
        "nombre_social": request.POST.get('nombre_social'),
        "pasaporte": request.POST.get('pasaporte'),
        "nip": request.POST.get('nie'),

        "fecha_nacimiento": request.POST.get('fecha_nacimiento'),
        "sexo": request.POST.get('sexo'),
        "genero_id": request.POST.get('genero'),
        "estado_civil": request.POST.get('estado_civil'),

        "recien_nacido": bool(request.POST.get('recien_nacido')),
        "extranjero": bool(request.POST.get('extranjero')),
        "pueblo_indigena": bool(request.POST.get('pueblo_indigena')),
        "fallecido": bool(request.POST.get('fallecido')),
        "fecha_fallecimiento": request.POST.get('fecha_fallecimiento'),

        "rut_madre": request.POST.get('rut_madre'),
        "nombres_madre": request.POST.get('nombres_madre'),
        "nombres_padre": request.POST.get('nombres_padre'),
        "nombre_pareja": request.POST.get('nombre_pareja'),
        "representante_legal": request.POST.get('representante_legal'),
        "rut_responsable_temporal": request.POST.get('rut_responsable_temporal'),
        "usar_rut_madre_como_responsable": bool(
            request.POST.get('usar_rut_madre_como_responsable')
        ),

        "direccion": request.POST.get('direccion'),
        "comuna": request.POST.get('comuna'),
        "ocupacion": request.POST.get('ocupacion'),
        "numero_telefono1": request.POST.get('numero_telefono1'),
        "numero_telefono2": request.POST.get('numero_telefono2'),

        # FICHAS
        "ficha": request.POST.get('ficha'),
    }


def parse_fecha(fecha_str):
    if not fecha_str:
        return None
    try:
        return datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return None


@transaction.atomic
def paciente_view(request, paciente_id=None):
    paciente_instance = None
    ficha_instance = None

    if request.method == 'POST':

        paciente_id_post = request.POST.get('paciente_id')

        if paciente_id_post:
            paciente_instance = Paciente.objects.filter(
                pk=paciente_id_post
            ).first()

            if paciente_instance:
                ficha_instance = Ficha.objects.filter(
                    paciente=paciente_instance,
                    establecimiento=request.user.establecimiento
                ).first()

        paciente_form = PacienteForm(
            request.POST,
            instance=paciente_instance
        )
        ficha_form = FichaForm(
            request.POST,
            instance=ficha_instance
        )

        if paciente_form.is_valid() and ficha_form.is_valid():

            paciente = paciente_form.save(commit=False)
            paciente.usuario_modifica = request.user
            paciente.save()

            ficha = ficha_form.save(commit=False)
            ficha.paciente = paciente
            ficha.establecimiento = request.user.establecimiento
            ficha.usuario = request.user
            ficha.save()

            messages.success(request, 'Paciente y ficha guardados correctamente.')
            return redirect('paciente_view')

        else:
            messages.error(request, 'Por favor corrige los errores.')
            print(paciente_form.errors)
            print(ficha_form.errors)

    else:
        paciente_form = PacienteForm()
        ficha_form = FichaForm()

    return render(request, 'paciente/form.html', {
        'paciente_form': paciente_form,
        'ficha_form': ficha_form,
        'title': 'Consulta de pacientes'
    })
