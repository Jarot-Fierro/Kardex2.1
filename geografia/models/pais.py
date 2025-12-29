from django.db import models
from simple_history.models import HistoricalRecords

from core.models import StandardModel


class Pais(StandardModel):
    nombre = models.CharField(max_length=100, unique=True, null=False, verbose_name='Nombre del País')
    cod_pais = models.CharField(max_length=10, null=True, blank=True, verbose_name='Código del País')

    history = HistoricalRecords()

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.upper()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'País'
        verbose_name_plural = 'Países'
