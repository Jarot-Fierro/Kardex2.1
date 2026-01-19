from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from clinica.models import MovimientoFicha
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

    # 3️⃣ Movimientos SOLO del establecimiento del usuario
    movimientos = (
        MovimientoFicha.objects
        .filter(
            ficha__paciente=paciente,
            establecimiento=establecimiento
        )
        .select_related(
            "ficha",
            "servicio_clinico_envio",
            "servicio_clinico_recepcion",
            "servicio_clinico_traspaso",
            "usuario_envio",
            "usuario_recepcion",
            "usuario_traspaso",
            "profesional_envio",
            "profesional_recepcion",
            "profesional_traspaso",
        )
        .order_by("-fecha_envio", "-created_at")
    )

    # 4️⃣ Payload
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
        "total_movimientos": movimientos.count(),
        "movimientos": []
    }

    for m in movimientos:
        data["movimientos"].append({
            # Ficha
            "ficha_id": m.ficha.id,
            "numero_ficha_sistema": m.ficha.numero_ficha_sistema,

            # Fechas
            "fecha_envio": m.fecha_envio.isoformat() if m.fecha_envio else None,
            "fecha_recepcion": m.fecha_recepcion.isoformat() if m.fecha_recepcion else None,
            "fecha_traspaso": m.fecha_traspaso.isoformat() if m.fecha_traspaso else None,

            # Estados
            "estado_envio": m.estado_envio,
            "estado_recepcion": m.estado_recepcion,
            "estado_traspaso": m.estado_traspaso,

            # Servicios
            "servicio_envio": (
                m.servicio_clinico_envio.nombre
                if m.servicio_clinico_envio else None
            ),
            "servicio_recepcion": (
                m.servicio_clinico_recepcion.nombre
                if m.servicio_clinico_recepcion else None
            ),
            "servicio_traspaso": (
                m.servicio_clinico_traspaso.nombre
                if m.servicio_clinico_traspaso else None
            ),

            # Usuarios
            "usuario_envio": (
                m.usuario_envio.username
                if m.usuario_envio else None
            ),
            "usuario_recepcion": (
                m.usuario_recepcion.username
                if m.usuario_recepcion else None
            ),
            "usuario_traspaso": (
                m.usuario_traspaso.username
                if m.usuario_traspaso else None
            ),

            # Profesionales
            "profesional_envio": (
                m.profesional_envio.nombres
                if m.profesional_envio else None
            ),
            "profesional_recepcion": (
                m.profesional_recepcion.nombres
                if m.profesional_recepcion else None
            ),
            "profesional_traspaso": (
                m.profesional_traspaso.nombres
                if m.profesional_traspaso else None
            ),

            # Observaciones
            "observacion_envio": m.observacion_envio,
            "observacion_recepcion": m.observacion_recepcion,
            "observacion_traspaso": m.observacion_traspaso,
        })

    return JsonResponse(data, safe=True)
