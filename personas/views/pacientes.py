from datetime import datetime

from django.contrib import messages
from django.db import transaction, IntegrityError
from django.shortcuts import render, redirect

from clinica.forms.ficha import FichaForm
from clinica.models import Ficha
from personas.forms.pacientes import PacienteForm
from personas.models.pacientes import Paciente


def parse_fecha(fecha_str):
    if not fecha_str:
        return None
    try:
        return datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def paciente_view(request, paciente_id=None):
    paciente_instance = None
    ficha_instance = None
    modo = "consulta"

    return render(request, 'paciente/form.html', {
        'paciente_form': paciente_form,
        'ficha_form': ficha_form,
        'modo': modo,
        'accion': request.POST.get('accion', 'ACTUALIZAR' if paciente_id else 'CREAR'),
        'paciente_id': request.POST.get('paciente_id', paciente_id),
        'title': 'Consulta de pacientes'
    })


def manejar_get(request, paciente_id=None):
    # GET
    if paciente_id:
        paciente_instance = Paciente.objects.filter(pk=paciente_id).first()

        if paciente_instance:
            ficha_instance = Ficha.objects.filter(
                paciente=paciente_instance,
                establecimiento=request.user.establecimiento
            ).first()

    paciente_form = PacienteForm(instance=paciente_instance)
    ficha_form = FichaForm(instance=ficha_instance)


def manejar_post(request, paciente_id=None):
    accion = request.POST.get('accion')
    paciente_id_post = request.POST.get('paciente_id') or paciente_id
    es_edicion = (accion == 'ACTUALIZAR') or bool(paciente_id_post)

    if es_edicion and paciente_id_post:
        paciente_instance = Paciente.objects.filter(pk=paciente_id_post).first()

        if paciente_instance:
            ficha_instance = Ficha.objects.filter(
                paciente=paciente_instance,
                establecimiento=request.user.establecimiento
            ).first()

    paciente_form = PacienteForm(request.POST, instance=paciente_instance)
    ficha_form = FichaForm(request.POST, instance=ficha_instance)

    if paciente_form.is_valid() and ficha_form.is_valid():

        # Verificación de consistencia Accion vs Instancia
        rut_post = paciente_form.cleaned_data.get('rut')
        if accion == 'CREAR':
            if Paciente.objects.filter(rut=rut_post).exists():
                paciente_form.add_error('rut',
                                        'Ya existe un paciente con este RUT. Por favor, consúltelo antes de intentar crear uno nuevo.')
                return render(request, 'paciente/form.html', {
                    'paciente_form': paciente_form,
                    'ficha_form': ficha_form,
                    'modo': 'error_crear',
                    'accion': accion,
                    'paciente_id': paciente_id_post,
                    'title': 'Consulta de pacientes'
                })
        elif accion == 'ACTUALIZAR':
            if not paciente_instance:
                messages.error(request,
                               'Error de consistencia: Se intentó actualizar un paciente que no existe o no fue cargado correctamente.')
                return redirect('paciente_view')

        try:
            with transaction.atomic():

                paciente = paciente_form.save(commit=False)
                es_creacion = paciente.pk is None

                paciente.usuario_modifica = request.user
                paciente.save()

                ficha = ficha_form.save(commit=False)
                ficha.paciente = paciente
                ficha.establecimiento = request.user.establecimiento
                ficha.usuario = request.user
                ficha.save()

        except IntegrityError:
            ficha_form.add_error(
                'numero_ficha_sistema',
                'Ya existe una ficha con este número para este establecimiento.'
            )

            modo = "error_actualizar" if es_edicion else "error_crear"

            return render(request, 'paciente/form.html', {
                'paciente_form': paciente_form,
                'ficha_form': ficha_form,
                'modo': modo,
                'accion': accion,
                'paciente_id': paciente_id_post,
                'title': 'Consulta de pacientes'
            })

        # ÉXITO
        if es_creacion:
            messages.success(request, 'Paciente y ficha creados correctamente.')
            modo = "creado"
        else:
            messages.info(request, 'Paciente y ficha actualizados correctamente.')
            modo = "actualizado"

        return redirect('paciente_view_param', paciente_id=paciente.id)

    else:
        # ERRORES DE VALIDACIÓN
        messages.error(request, 'Por favor corrige los errores.')
        modo = "error_actualizar" if es_edicion else "error_crear"
