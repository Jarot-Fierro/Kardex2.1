from django.db.models.signals import post_save
from django.dispatch import receiver

from kardex.models import Paciente


@receiver(post_save, sender=Paciente)
def asignar_codigo_paciente(sender, instance, created, **kwargs):
    # Dejar como respaldo: si por alguna razón el código no fue asignado en save(),
    # actualizarlo sin disparar señales ni historial adicional.
    if created and not instance.codigo:
        Paciente.objects.filter(pk=instance.pk, codigo__isnull=True).update(
            codigo=f"PAC-{instance.pk:07d}"
        )
