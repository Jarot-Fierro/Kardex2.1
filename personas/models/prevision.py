from django.db import models
from simple_history.models import HistoricalRecords

from core.models import StandardModel


class Prevision(StandardModel):
    nombre = models.CharField(max_length=100, unique=True, null=False, verbose_name='Nombre')
    codigo = models.IntegerField(null=True, blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.upper()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Prevision'
        verbose_name_plural = 'Previsiones'
