from django.db.models import Prefetch
from django.http import JsonResponse

from clinica.models import Ficha, MovimientoFicha
from personas.models.pacientes import Paciente


def get_paciente_ficha(request, rut):
    paciente = (
        Paciente.objects.filter(rut=rut)
        .select_related("comuna", "prevision", "usuario", "usuario_anterior")
        .first()
    )

    if not paciente:
        return JsonResponse(
            {"error": "Paciente no encontrado"},
            status=404
        )

    ficha = (
        Ficha.objects.filter(paciente=paciente)
        .select_related("sector", "establecimiento", "usuario")
        .prefetch_related(
            Prefetch(
                "movimientoficha_set",
                queryset=MovimientoFicha.objects.order_by("-fecha_envio"),
                to_attr="movimientos"
            )
        )
        .first()
    )
    todas_las_fichas = (
        Ficha.objects
        .filter(paciente=paciente)
        .select_related("establecimiento")
    )

    data = {
        "paciente": {
            "codigo": paciente.codigo,
            "rut": paciente.rut,
            "nip": paciente.nip,
            "nombre": paciente.nombre,
            "apellido_paterno": paciente.apellido_paterno,
            "apellido_materno": paciente.apellido_materno,
            "nombre_social": paciente.nombre_social,
            "genero": paciente.genero,
            "estado_civil": paciente.estado_civil,
            "fecha_nacimiento": paciente.fecha_nacimiento,
            "sexo": paciente.sexo,
            "pueblo_indigena": paciente.pueblo_indigena,
            "rut_madre": paciente.rut_madre,
            "rut_responsable_temporal": paciente.rut_responsable_temporal,
            "usar_rut_madre_como_responsable": paciente.usar_rut_madre_como_responsable,
            "pasaporte": paciente.pasaporte,
            "nombres_padre": paciente.nombres_padre,
            "nombres_madre": paciente.nombres_madre,
            "nombre_pareja": paciente.nombre_pareja,
            "representante_legal": paciente.representante_legal,
            "direccion": paciente.direccion,
            "numero_telefono1": paciente.numero_telefono1,
            "numero_telefono2": paciente.numero_telefono2,
            "ocupacion": paciente.ocupacion,
            "alergico_a": paciente.alergico_a,
            "recien_nacido": paciente.recien_nacido,
            "extranjero": paciente.extranjero,
            "fallecido": paciente.fallecido,
            "fecha_fallecimiento": paciente.fecha_fallecimiento,
            "comuna": paciente.comuna.nombre if paciente.comuna else None,
            "prevision": paciente.prevision.nombre if paciente.prevision else None,
            "usuario_creador": paciente.usuario.username if paciente.usuario else None,
            "usuario_anterior": paciente.usuario_anterior.nombre if paciente.usuario_anterior else None,
        },
        "ficha": None
    }

    if ficha:
        data["ficha"] = {
            "numero_ficha_sistema": ficha.numero_ficha_sistema,
            "numero_ficha_tarjeta": ficha.numero_ficha_tarjeta,
            "pasivado": ficha.pasivado,
            "observacion": ficha.observacion,
            "fecha_creacion": ficha.created_at,
            "fecha_modificacion": ficha.updated_at,
            "fecha_creacion_anterior": ficha.fecha_creacion_anterior,
            "usuario": ficha.usuario.username if ficha.usuario else None,
            "establecimiento": ficha.establecimiento.nombre if ficha.establecimiento else None,
            "sector": ficha.sector.nombre if ficha.sector else None,
            "movimientos": [
                {
                    "fecha_envio": m.fecha_envio,
                    "origen": m.origen.nombre if m.origen else None,
                    "destino": m.destino.nombre if m.destino else None,
                    "observacion": m.observacion,
                    "profesional": m.profesional,
                }
                for m in getattr(ficha, "movimientos", [])
            ],
            "otras_fichas": [
                {
                    "numero_ficha_sistema": f.numero_ficha_sistema,
                    "establecimiento": f.establecimiento.nombre if f.establecimiento else None,
                }
                for f in todas_las_fichas
                if f.id != ficha.id
            ]

        }

    return JsonResponse(data)
