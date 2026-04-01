from django.core.exceptions import ValidationError
from django.db import transaction

from clinica.models.ficha import Ficha
from clinica.models.movimiento_ficha import MovimientoFicha
from personas.models.pacientes import Paciente
from .models import FusionFicha


def fusionar_pacientes_clinicos(
        paciente_ficticio,
        paciente_real,
        ficha_a_conservar,
        ficha_a_eliminar,
        movimientos_ficticio_ids,
        movimientos_real_ids,
        usuario,
        motivo_fusion=None,
        borrar_paciente_ficticio=False
):
    """
    Realiza la fusión de un paciente ficticio con uno real de forma atómica.
    """
    with transaction.atomic():
        # Referencia original para saber cuál ficha se conserva
        ficha_a_conservar_original_ref = ficha_a_conservar

        # Validaciones básicas
        if paciente_ficticio == paciente_real:
            raise ValidationError("El paciente ficticio y el real no pueden ser el mismo.")

        # Obtener los objetos frescos de la BD para asegurar estado actual
        paciente_ficticio = Paciente.objects.select_for_update().get(pk=paciente_ficticio.pk)
        paciente_real = Paciente.objects.select_for_update().get(pk=paciente_real.pk)

        # 1. Traspasar movimientos de la ficha a eliminar a la ficha a conservar
        if ficha_a_eliminar:
            ficha_del = Ficha.objects.select_for_update().get(pk=ficha_a_eliminar.pk)
            MovimientoFicha.objects.filter(ficha=ficha_del).update(ficha=ficha_a_conservar)

            # Si existen otros modelos relacionados, se deberían mover aquí también.
            try:
                from clinica.models.movimiento_ficha_monologo_controlado import MovimientoMonologoControlado
                MovimientoMonologoControlado.objects.filter(ficha=ficha_del).update(
                    ficha=ficha_a_conservar,
                    rut_paciente=paciente_real
                )
            except ImportError:
                pass

        # 2. Registrar respaldo de fusión ANTES de eliminar registros
        se_queda_primera = (ficha_a_conservar == ficha_a_conservar_original_ref)
        FusionFicha.objects.create(
            paciente_ficticio_id=paciente_ficticio.pk,
            paciente_real_id=paciente_real.pk,
            rut_ficticio=paciente_ficticio.rut,
            rut_real=paciente_real.rut,
            nombres=paciente_ficticio.nombre,
            apellidos=f"{paciente_ficticio.apellido_paterno} {paciente_ficticio.apellido_materno}",
            nombres_real=paciente_real.nombre,
            apellidos_real=f"{paciente_real.apellido_paterno} {paciente_real.apellido_materno}",
            sexo=paciente_real.sexo,
            numero_ficha_sistema=ficha_a_conservar.numero_ficha_sistema,
            numero_ficha_sistema_real=ficha_a_eliminar.numero_ficha_sistema if ficha_a_eliminar else None,
            fecha_creacion_anterior=paciente_ficticio.created_at,
            fecha_creacion_actual=paciente_real.created_at,
            se_queda_primera_ficha=se_queda_primera,
            se_queda_segunda_ficha=not se_queda_primera,
            establecimiento=ficha_a_conservar.establecimiento,
            created_by=usuario
        )

        # 3. Asignar el paciente real a la ficha a conservar
        ficha_a_conservar.paciente = paciente_real
        ficha_a_conservar.observacion = (
                                                ficha_a_conservar.observacion or "") + f"\nFusión realizada por {usuario}. Paciente ficticio {paciente_ficticio.pk} fusionado. Motivo: {motivo_fusion}"
        ficha_a_conservar.save()

        # 4. Eliminar la ficha sobrante
        if ficha_a_eliminar:
            ficha_del.delete()

        # 5. Borrar o desactivar el paciente ficticio
        if borrar_paciente_ficticio:
            paciente_ficticio.delete()
        else:
            paciente_ficticio.status = False
            # No modificar nombre ni rut del paciente si decide dejarlo
            # Ingresar en alergico a: el campo del paciente que se le quitó la ficha n°
            if ficha_a_eliminar:
                numero_ficha_removida = ficha_a_eliminar.numero_ficha_sistema
                mensaje_alergia = f"SE LE QUITO LA FICHA N° {numero_ficha_removida} POR FUSION"
                if paciente_ficticio.alergico_a:
                    paciente_ficticio.alergico_a = f"{paciente_ficticio.alergico_a} | {mensaje_alergia}"
                else:
                    paciente_ficticio.alergico_a = mensaje_alergia

            paciente_ficticio.save()

    return True
