from django.db import models
from simple_history.models import HistoricalRecords

from core.models import StandardModel


class Ficha(StandardModel):
    numero_ficha_sistema = models.IntegerField(null=True, blank=True, verbose_name='Número de Ficha')
    numero_ficha_tarjeta = models.IntegerField(null=True, blank=True,
                                               verbose_name='Número de Ficha Tarjeta')
    pasivado = models.BooleanField(default=False, verbose_name='Pasivado')
    observacion = models.TextField(null=True, blank=True, verbose_name='Observación')

    usuario = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True, blank=True,
                                verbose_name='Usuario', related_name='fichas_usuarios')

    fecha_creacion_anterior = models.DateTimeField(null=True, blank=True)

    paciente = models.ForeignKey('personas.Paciente', on_delete=models.PROTECT, null=True, blank=True,
                                 verbose_name='Paciente', related_name='fichas_pacientes')

    establecimiento = models.ForeignKey('establecimientos.Establecimiento', on_delete=models.PROTECT, null=True,
                                        blank=True,
                                        verbose_name='Establecimiento', related_name='fichas_establecimientos')

    sector = models.ForeignKey('establecimientos.Sector', on_delete=models.PROTECT, null=True, blank=True,
                               verbose_name='Sector', related_name='fichas_sectores')

    history = HistoricalRecords()

    def __str__(self):
        num = self.numero_ficha_sistema

        numero = f"{num:04d}" if num is not None else "----"

        if self.paciente:
            nombre = self.paciente.nombre or ""
            ap_paterno = self.paciente.apellido_paterno or ""
            ap_materno = self.paciente.apellido_materno or ""
            codigo = self.paciente.codigo or ""

            nombre_completo = f"{nombre} {ap_paterno} {ap_materno}".strip()

            if nombre_completo.strip():
                return f"Ficha #{numero} - {nombre_completo}"
            else:
                return f"Ficha #{numero} - Código paciente: {codigo}"
        else:
            return f"Ficha #{numero} - Sin paciente"

    def save(self, *args, **kwargs):
        creando = self.pk is None
        super().save(*args, **kwargs)  # Guardamos primero para tener el PK

        if creando and not self.numero_ficha_sistema and self.establecimiento:
            # Obtener el máximo actual
            max_ficha = Ficha.objects.filter(establecimiento=self.establecimiento) \
                .exclude(pk=self.pk) \
                .aggregate(models.Max('numero_ficha_sistema'))['numero_ficha_sistema__max']

            if max_ficha is not None:
                self.numero_ficha_sistema = max_ficha + 1
            else:
                # Fallback: usar el ID como número de ficha si no hay registros
                self.numero_ficha_sistema = self.pk

            # Guardamos solo el campo actualizado para evitar loops
            super().save(update_fields=['numero_ficha_sistema'])

    class Meta:
        verbose_name = 'Ficha'
        verbose_name_plural = 'Fichas'
        constraints = [
            models.UniqueConstraint(
                fields=['numero_ficha_sistema', 'establecimiento'],
                name='unique_ficha_por_establecimiento'
            )
        ]
