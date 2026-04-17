from django.core.exceptions import ValidationError
from django.db import transaction

from clinica.models.ficha import Ficha
from clinica.models.movimiento_ficha import MovimientoFicha
from personas.models.pacientes import Paciente
from respaldos.models.respaldo_ficha import RespaldoFicha
from respaldos.models.respaldo_paciente import RespaldoPaciente
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

        # 1. Traspasar TODOS los movimientos del paciente ficticio a la ficha a conservar
        # Independiente de si vienen en movimientos_ficticio_ids o no, buscamos por paciente
        # para asegurar que no queden registros huérfanos o protegidos.
        movimientos_ficticio_qs = MovimientoFicha.objects.filter(ficha__paciente=paciente_ficticio).select_for_update()
        movimientos_ficticio_qs.update(ficha=ficha_a_conservar)

        # Traspasar también movimientos de monólogo controlado si existen
        try:
            from clinica.models.movimiento_ficha_monologo_controlado import MovimientoMonologoControlado
            movimientos_monologo = MovimientoMonologoControlado.objects.filter(
                ficha__paciente=paciente_ficticio
            ).select_for_update()
            
            for mov in movimientos_monologo:
                mov.ficha = ficha_a_conservar
                mov.rut_paciente = paciente_real
                # Si el modelo tiene campo 'rut' (string), también actualizarlo
                if hasattr(mov, 'rut'):
                    mov.rut = paciente_real.rut
                mov.save()
        except (ImportError, Exception):
            pass

        # Si había una ficha específica a eliminar en este establecimiento
        if ficha_a_eliminar:
            ficha_del = Ficha.objects.select_for_update().get(pk=ficha_a_eliminar.pk)
            # Los movimientos ya fueron movidos arriba por paciente_ficticio, 
            # pero por seguridad aseguramos los que queden en esta ficha específica
            MovimientoFicha.objects.filter(ficha=ficha_del).update(ficha=ficha_a_conservar)

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
            # Crear respaldo de la ficha antes de eliminarla
            RespaldoFicha.objects.create(
                numero_ficha_sistema=ficha_del.numero_ficha_sistema,
                numero_ficha_tarjeta=ficha_del.numero_ficha_tarjeta,
                numero_ficha_respaldo=ficha_del.numero_ficha_respaldo,
                rut=paciente_ficticio.rut,
                observacion=ficha_del.observacion,
                usuario=ficha_del.usuario,
                usuario_anterior=ficha_del.usuario_anterior,
                rut_anterior=ficha_del.rut_anterior,
                fecha_creacion_anterior=ficha_del.created_at,
                paciente=paciente_ficticio,
                fecha_mov=ficha_del.fecha_mov,
                establecimiento=ficha_del.establecimiento,
                sector=ficha_del.sector,
                usuario_eliminacion=usuario,
                motivo_eliminacion=f"Fusión de pacientes. Motivo original: {motivo_fusion}"
            )
            ficha_del.delete()

        # 5. Borrar o desactivar el paciente ficticio
        if borrar_paciente_ficticio:
            # Crear respaldo del paciente antes de eliminarlo
            RespaldoPaciente.objects.create(
                ficha=ficha_a_eliminar.numero_ficha_sistema if ficha_a_eliminar else None,
                codigo=paciente_ficticio.codigo,
                id_anterior=paciente_ficticio.id_anterior,
                rut=paciente_ficticio.rut,
                nip=paciente_ficticio.nip,
                nombre=paciente_ficticio.nombre,
                rut_madre=paciente_ficticio.rut_madre,
                apellido_paterno=paciente_ficticio.apellido_paterno,
                apellido_materno=paciente_ficticio.apellido_materno,
                pueblo_indigena=paciente_ficticio.pueblo_indigena,
                rut_responsable_temporal=paciente_ficticio.rut_responsable_temporal,
                usar_rut_madre_como_responsable=paciente_ficticio.usar_rut_madre_como_responsable,
                pasaporte=paciente_ficticio.pasaporte,
                nombre_social=paciente_ficticio.nombre_social,
                fecha_nacimiento=paciente_ficticio.fecha_nacimiento,
                sexo=paciente_ficticio.sexo,
                estado_civil=paciente_ficticio.estado_civil,
                nombres_padre=paciente_ficticio.nombres_padre,
                nombres_madre=paciente_ficticio.nombres_madre,
                nombre_pareja=paciente_ficticio.nombre_pareja,
                representante_legal=paciente_ficticio.representante_legal,
                direccion=paciente_ficticio.direccion,
                sin_telefono=paciente_ficticio.sin_telefono,
                numero_telefono1=paciente_ficticio.numero_telefono1,
                numero_telefono2=paciente_ficticio.numero_telefono2,
                ocupacion=paciente_ficticio.ocupacion,
                recien_nacido=paciente_ficticio.recien_nacido,
                extranjero=paciente_ficticio.extranjero,
                fallecido=paciente_ficticio.fallecido,
                fecha_fallecimiento=paciente_ficticio.fecha_fallecimiento,
                alergico_a=paciente_ficticio.alergico_a,
                comuna=paciente_ficticio.comuna,
                prevision=paciente_ficticio.prevision,
                genero=paciente_ficticio.genero,
                usuario=paciente_ficticio.usuario,
                usuario_anterior=paciente_ficticio.usuario_anterior,
                usuario_eliminacion=usuario,
                motivo_eliminacion=f"Fusión de pacientes. Motivo original: {motivo_fusion}"
            )
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
