from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from clinica.models import Ficha, MovimientoMonologoControlado
from personas.models.pacientes import Paciente


@login_required
def get_movimientos_paciente_establecimiento(request, rut):
    # 1️⃣ Usuario logueado
    usuario = request.user
    establecimiento = getattr(usuario, "establecimiento", None)

    if not establecimiento:
        return JsonResponse(
            {"error": "Usuario no asociado a un establecimiento"},
            status=403
        )

    # 2️⃣ Buscar paciente
    paciente = Paciente.objects.filter(rut=rut).first()

    if not paciente:
        return JsonResponse(
            {"error": "Paciente no encontrado"},
            status=404
        )

    # 3️⃣ Buscar Ficha para este establecimiento
    ficha = Ficha.objects.filter(paciente=paciente, establecimiento=establecimiento).first()
    if not ficha:
        return JsonResponse(
            {"error": "Ficha no encontrada para este paciente en este establecimiento"},
            status=404
        )

    # 4️⃣ Información de ingreso (Lógica solicitada)
    # primero ingresado por se saca del modelo de ficha el campo de usuario_anterior
    # prioridad usuario_anterior, si no existe se muestra created_by
    ingresado_por = ""
    if ficha.usuario_anterior:
        ingresado_por = f"{ficha.usuario_anterior.nombre} (Migrado)"
    elif ficha.created_by:
        ingresado_por = ficha.created_by.username

    # segundo fecha ingreso al sistema sería lo mismo, se saca de ficha
    # prioridad el campo de fecha_creacion_anterior, si no created_at.
    fecha_ingreso = ficha.fecha_creacion_anterior or ficha.created_at

    # 5️⃣ Ubicación actual (Último MovimientoMonologoControlado con estado 'E')
    ultimo_mov = MovimientoMonologoControlado.objects.filter(
        ficha=ficha,
        establecimiento=establecimiento,
        estado='E',
        status=True
        # establecimiento=establecimiento # Generalmente la ficha ya está ligada al establecimiento
    ).order_by("-fecha_salida", "-created_at").first()

    ubicacion = {
        "servicio_clinico": None,
        "profesional_cargo": None,
        "fecha_hora_envio": None,
        "estado": None
    }

    if ultimo_mov:
        ubicacion["estado"] = ultimo_mov.estado
        if ultimo_mov.estado == 'E':
            ubicacion["servicio_clinico"] = (
                ultimo_mov.servicio_clinico_destino.nombre
                if ultimo_mov.servicio_clinico_destino else None
            )
            ubicacion["profesional_cargo"] = (
                ultimo_mov.profesional.nombres
                if ultimo_mov.profesional else (ultimo_mov.profesional_anterior or None)
            )
            ubicacion["fecha_hora_envio"] = ultimo_mov.fecha_salida.isoformat() if ultimo_mov.fecha_salida else None

    # 6️⃣ Listado de movimientos (MovimientoMonologoControlado)
    movimientos_qs = (
        MovimientoMonologoControlado.objects
        .filter(ficha=ficha, establecimiento=establecimiento, status=True)
        .select_related(
            "servicio_clinico_destino",
            "profesional",
            "usuario_entrega_id",
            "usuario_entrada_id"
        )
        .order_by("-fecha_salida", "-created_at")
    )

    # 7️⃣ Payload
    data = {
        "establecimiento": {
            "id": establecimiento.id,
            "nombre": establecimiento.nombre,
        },
        "paciente": {
            "id": paciente.id,
            "rut": paciente.rut,
            "nombre": paciente.nombre,
            "apellido_paterno": paciente.apellido_paterno,
            "apellido_materno": paciente.apellido_materno,
        },
        "ficha": {
            "id": ficha.id,
            "numero_ficha_sistema": ficha.numero_ficha_sistema,
            "ingresado_por": ingresado_por,
            "fecha_ingreso": fecha_ingreso.isoformat() if fecha_ingreso else None,
            "ubicacion_actual": ubicacion,
        },
        "total_movimientos": movimientos_qs.count(),
        "movimientos": []
    }

    for m in movimientos_qs:
        data["movimientos"].append({
            "id": m.id,
            "fecha_envio": m.fecha_salida.isoformat() if m.fecha_salida else None,
            "fecha_recepcion": m.fecha_entrada.isoformat() if m.fecha_entrada else None,
            "fecha_traspaso": m.fecha_traspaso.isoformat() if m.fecha_traspaso else None,
            "estado": m.get_estado_display(),
            "estado_code": m.estado,
            "destino": (
                m.servicio_clinico_destino.nombre
                if m.servicio_clinico_destino else None
            ),
            "profesional": (
                m.profesional.nombres
                if m.profesional else (m.profesional_anterior or None)
            ),
            "usuario_envio": (
                m.usuario_entrega_id.nombre
                if m.usuario_entrega_id else (m.usuario_entrega or None)
            ),
            "usuario_recepcion": (
                m.usuario_entrada_id.nombre
                if m.usuario_entrada_id else (m.usuario_entrada or None)
            ),
            "observacion_envio": m.observacion_salida,
            "observacion_recepcion": m.observacion_entrada,
            "observacion_traspaso": m.observacion_traspaso,
        })

    return JsonResponse(data, safe=True)
