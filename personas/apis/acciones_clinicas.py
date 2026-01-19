import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from clinica.models import Ficha
from core.validations import validate_rut, format_rut
from personas.models.pacientes import Paciente


@login_required
@require_POST
def actualizar_rut_paciente(request):
    try:
        data = json.loads(request.body)
        paciente_id = data.get('paciente_id')
        nuevo_rut = data.get('nuevo_rut')

        if not nuevo_rut or not validate_rut(nuevo_rut):
            return JsonResponse({"error": "RUT inválido"}, status=400)

        nuevo_rut = format_rut(nuevo_rut)

        # Verificar si ya existe otro paciente con ese RUT
        if Paciente.objects.filter(rut=nuevo_rut).exclude(id=paciente_id).exists():
            return JsonResponse({"error": "Ya existe otro paciente con ese RUT"}, status=400)

        with transaction.atomic():
            paciente = Paciente.objects.select_for_update().get(pk=paciente_id)
            paciente.rut = nuevo_rut
            paciente.save()

            return JsonResponse({"success": True, "rut": nuevo_rut})
    except Paciente.DoesNotExist:
        return JsonResponse({"error": "Paciente no encontrado"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
def toggle_pasivado_ficha(request):
    try:
        data = json.loads(request.body)
        paciente_id = data.get('paciente_id')

        with transaction.atomic():
            ficha = Ficha.objects.select_for_update().get(
                paciente_id=paciente_id,
                establecimiento=request.user.establecimiento
            )
            ficha.pasivado = not ficha.pasivado
            ficha.save()

            return JsonResponse({
                "success": True,
                "pasivado": ficha.pasivado
            })
    except Ficha.DoesNotExist:
        return JsonResponse({"error": "Ficha no encontrada para este establecimiento"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
def asignar_numero_ficha(request):
    try:
        data = json.loads(request.body)
        paciente_id = data.get('paciente_id')
        nuevo_numero = data.get('nuevo_numero')
        es_tarjeta = data.get('es_tarjeta', False)

        if not nuevo_numero:
            return JsonResponse({"error": "Número de ficha requerido"}, status=400)

        with transaction.atomic():
            ficha = Ficha.objects.select_for_update().get(
                paciente_id=paciente_id,
                establecimiento=request.user.establecimiento
            )

            # Verificar duplicidad en el mismo establecimiento
            if Ficha.objects.filter(
                    numero_ficha_sistema=nuevo_numero,
                    establecimiento=request.user.establecimiento
            ).exclude(pk=ficha.pk).exists():
                return JsonResponse({"error": "Este número de ficha ya existe en este establecimiento"}, status=400)

            # Respaldo del número actual
            ficha.numero_ficha_respaldo = ficha.numero_ficha_sistema
            ficha.numero_ficha_sistema = nuevo_numero

            if es_tarjeta:
                ficha.numero_ficha_tarjeta = nuevo_numero

            ficha.save()

            return JsonResponse({
                "success": True,
                "numero_ficha_sistema": ficha.numero_ficha_sistema,
                "numero_ficha_tarjeta": ficha.numero_ficha_tarjeta,
                "numero_ficha_respaldo": ficha.numero_ficha_respaldo
            })
    except Ficha.DoesNotExist:
        return JsonResponse({"error": "Ficha no encontrada"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
