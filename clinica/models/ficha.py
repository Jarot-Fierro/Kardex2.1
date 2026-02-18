from django.db import models
from simple_history.models import HistoricalRecords

from core.models import StandardModel


class Ficha(StandardModel):
    numero_ficha_sistema = models.IntegerField(null=True, blank=True, verbose_name='Número de Ficha')
    numero_ficha_tarjeta = models.IntegerField(null=True, blank=True,
                                               verbose_name='Número de Ficha Tarjeta')
    numero_ficha_respaldo = models.IntegerField(null=True, blank=True,
                                                verbose_name='Número de Ficha Respaldo')
    pasivado = models.BooleanField(default=False, verbose_name='Pasivado')
    observacion = models.TextField(null=True, blank=True, verbose_name='Observación')

    usuario = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True, blank=True,
                                verbose_name='Usuario', related_name='fichas_usuarios')

    usuario_anterior = models.ForeignKey('personas.UsuarioAnterior', on_delete=models.PROTECT, null=True, blank=True,
                                         verbose_name='Usuario Anterior', related_name='fichas_usuarios_anteriores')

    rut_anterior = models.CharField(max_length=50, null=True, blank=True,
                                    verbose_name='RUT Anterior del Usuario')

    fecha_creacion_anterior = models.DateTimeField(null=True, blank=True)

    paciente = models.ForeignKey('personas.Paciente', on_delete=models.PROTECT, null=True, blank=True,
                                 verbose_name='Paciente', related_name='fichas_pacientes')

    fecha_mov = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Movimiento')

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
            nombre_completo = self.paciente.nombre_completo
            if nombre_completo:
                return f"Ficha #{numero} - {nombre_completo}"
            else:
                return f"Ficha #{numero} - Código paciente: {self.paciente.codigo or '----'}"
        else:
            return f"Ficha #{numero} - Sin paciente"

    def save(self, *args, **kwargs):
        # Determinamos si necesitamos asignar un número de ficha automáticamente
        # 1. Si no tiene número de ficha sistema
        # 2. Y tiene un establecimiento asignado
        if not self.numero_ficha_sistema and self.establecimiento:
            # Obtener el máximo actual en ese establecimiento
            max_ficha = Ficha.objects.filter(establecimiento=self.establecimiento) \
                .aggregate(models.Max('numero_ficha_sistema'))['numero_ficha_sistema__max']

            if max_ficha is not None:
                self.numero_ficha_sistema = max_ficha + 1
            else:
                # Fallback: si no hay registros previos con número, intentamos usar el PK si existe
                # o dejamos que el save posterior asigne un número basado en el PK si sigue vacío
                if self.pk:
                    self.numero_ficha_sistema = self.pk
                else:
                    # Si estamos creando, guardaremos primero para obtener el PK
                    pass

        super().save(*args, **kwargs)

        # Si después de guardar sigue sin número (caso de creación inicial sin registros previos)
        if not self.numero_ficha_sistema and self.pk:
            self.numero_ficha_sistema = self.pk
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
