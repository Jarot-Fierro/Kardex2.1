from django.http import JsonResponse
from django.shortcuts import render

from core.choices import ESTADO_CIVIL
from establecimientos.models.sectores import Sector
from geografia.models.comuna import Comuna
from personas.models.genero import Genero
from personas.models.prevision import Prevision


def capturar_datos_paciente(request):
    return {
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


def paciente_view(request):
    generos = Genero.objects.filter(status=True)
    previsiones = Prevision.objects.filter(status=True)
    comunas = Comuna.objects.filter(status=True)
    sectores = Sector.objects.filter(
        status=True,
        establecimiento=request.user.establecimiento
    )
    estado_civil = ESTADO_CIVIL

    if request.method == 'POST':
        datos = capturar_datos_paciente(request)

        # with transaction.atomic():
        #
        #     paciente_id = datos.get('paciente_id')
        #
        #     if paciente_id:
        #         # 🔁 ACTUALIZACIÓN
        #         paciente = Paciente.objects.select_for_update().get(
        #             id=paciente_id
        #         )
        #         accion = 'actualizado'
        #     else:
        #         # ➕ CREACIÓN
        #         paciente = Paciente(
        #             establecimiento=request.user.establecimiento
        #         )
        #         accion = 'creado'
        #
        #     # asignar campos
        #     paciente.nombre = datos['nombre']
        #     paciente.apellido_paterno = datos['apellido_paterno']
        #     paciente.apellido_materno = datos['apellido_materno']
        #     paciente.nombre_social = datos['nombre_social']
        #     paciente.pasaporte = datos['pasaporte']
        #     paciente.nip = datos['nip']
        #     paciente.fecha_nacimiento = datos['fecha_nacimiento']
        #     paciente.sexo = datos['sexo']
        #     paciente.genero_id = datos['genero']
        #     paciente.estado_civil = datos['estado_civil']
        #     paciente.recien_nacido = datos['recien_nacido']
        #     paciente.extranjero = datos['extranjero']
        #     paciente.pueblo_indigena = datos['pueblo_indigena']
        #     paciente.fallecido = datos['fallecido']
        #     paciente.fecha_fallecimiento = datos['fecha_fallecimiento']
        #     paciente.rut_madre = datos['rut_madre']
        #     paciente.nombres_madre = datos['nombres_madre']
        #     paciente.nombres_padre = datos['nombres_padre']
        #     paciente.nombre_pareja = datos['nombre_pareja']
        #     paciente.representante_legal = datos['representante_legal']
        #     paciente.rut_responsable_temporal = datos['rut_responsable_temporal']
        #     paciente.usar_rut_madre_como_responsable = datos['usar_rut_madre_como_responsable']
        #     paciente.direccion = datos['direccion']
        #     paciente.comuna_id = datos['comuna']
        #     paciente.ocupacion = datos['ocupacion']
        #     paciente.numero_telefono1 = datos['numero_telefono1']
        #     paciente.numero_telefono2 = datos['numero_telefono2']
        #     paciente.usuario_modifica = request.user
        #
        #     paciente.save()
        #
        #     ficha = Ficha.objects.filter(
        #         numero_ficha_sistema=datos['ficha'],
        #         establecimiento=request.user.establecimiento
        #     ).first()
        #
        #     if ficha:
        #         ficha.paciente = paciente
        #     else:
        #         ficha = Ficha.objects.create(
        #             numero_ficha_sistema=datos['ficha'],
        #             paciente=paciente,
        #             establecimiento=request.user.establecimiento,
        #             usuario_crea=request.user
        #         )

        return JsonResponse({
            'ok': True,
            'datos': datos,
        })

    return render(request, 'paciente/form.html', {
        'generos': generos,
        'previsiones': previsiones,
        'comunas': comunas,
        'sectores': sectores,
        'estado_civil': estado_civil,
        'title': 'Registro/Consulta de Paciente'
    })
