from django.db import models

from core.choices import SEXO_CHOICES
from core.models import StandardModel


class FusionFicha(StandardModel):
    # IDs de pacientes (real/ficticio)
    paciente_ficticio_id = models.IntegerField(verbose_name='ID Paciente Ficticio', null=True, blank=True)
    paciente_real_id = models.IntegerField(verbose_name='ID Paciente Real', null=True, blank=True)

    # Datos identificatorios
    rut_ficticio = models.CharField(max_length=100, verbose_name='RUT Ficticio', null=True, blank=True)
    rut_real = models.CharField(max_length=100, verbose_name='RUT Real', null=True, blank=True)

    nombres = models.CharField(max_length=200, verbose_name='Nombres')
    apellidos = models.CharField(max_length=200, verbose_name='Apellidos')

    nombres_real = models.CharField(max_length=200, verbose_name='Nombres Reales')
    apellidos_real = models.CharField(max_length=200, verbose_name='Apellidos Reales')

    sexo = models.CharField(max_length=50, choices=SEXO_CHOICES, verbose_name='Sexo', default='NO INFORMADO')

    # Datos de la ficha
    numero_ficha_sistema = models.IntegerField(verbose_name='Número Ficha Sistema', null=True, blank=True)
    numero_ficha_sistema_real = models.IntegerField(verbose_name='Número Ficha Sistema Real', null=True, blank=True)

    # Relación con el establecimiento (para saber dónde ocurrió la fusión)
    establecimiento = models.ForeignKey('establecimientos.Establecimiento', on_delete=models.SET_NULL, null=True,
                                        blank=True, verbose_name='Establecimiento',
                                        related_name='fusiones_fichas')

    fecha_creacion_anterior = models.DateTimeField(verbose_name='Fecha de Creación Anterior', null=True, blank=True)
    fecha_creacion_actual = models.DateTimeField(verbose_name='Fecha de Creación Actual en Sistema', null=True,
                                                 blank=True)

    # Checks para saber qué ficha se queda
    se_queda_primera_ficha = models.BooleanField(default=False, verbose_name='Se queda la primera ficha')
    se_queda_segunda_ficha = models.BooleanField(default=False, verbose_name='Se queda la segunda ficha')

    class Meta:
        verbose_name = 'Fusión de Ficha'
        verbose_name_plural = 'Fusiones de Fichas'

    def __str__(self):
        return f"Fusión Paciente Real ID: {self.paciente_real_id} - Ficha: {self.numero_ficha_sistema}"
