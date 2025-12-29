from django.db import models
from simple_history.models import HistoricalRecords

from core.models import StandardModel


class ServicioClinico(StandardModel):
    nombre = models.CharField(max_length=100, null=False, verbose_name='Nombre')
    tiempo_horas = models.IntegerField(null=True, blank=True, verbose_name='Tiempo en horas')
    correo_jefe = models.EmailField(max_length=100, null=True, blank=True, verbose_name='Correo del jefe a cargo')
    telefono = models.CharField(max_length=15, null=True, blank=True, verbose_name='Teléfono')

    establecimiento = models.ForeignKey('establecimientos.Establecimiento', null=True, blank=True,
                                        on_delete=models.SET_NULL,
                                        verbose_name='Establecimiento',
                                        related_name='servicios_clinicos_establecimiento')

    history = HistoricalRecords()

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.upper()

        if self.correo_jefe:
            self.correo_jefe = self.correo_jefe.lower()

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Servicio Clínico'
        verbose_name_plural = 'Servicios Clínicos'
