from django.db import models
from simple_history.models import HistoricalRecords

from core.models import StandardModel


class Establecimiento(StandardModel):
    nombre = models.CharField(max_length=100, unique=True, null=False, verbose_name='Nombre')
    direccion = models.CharField(max_length=200, null=True, blank=True, verbose_name='Dirección')
    telefono = models.CharField(max_length=15, null=True, blank=True, verbose_name='Teléfono')
    comuna = models.ForeignKey('geografia.Comuna', on_delete=models.PROTECT, null=False, verbose_name='Comuna'
                               , related_name='establecimientos_comuna')
    history = HistoricalRecords()

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.upper()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Establecimiento'
        verbose_name_plural = 'Establecimientos'
