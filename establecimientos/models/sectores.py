from django.db import models
from simple_history.models import HistoricalRecords

from core.models import StandardModel
from establecimientos.models.colores import Color


class Sector(StandardModel):
    codigo = models.CharField(null=True, blank=True, verbose_name='Código del Sector', max_length=100)
    color = models.ForeignKey(Color, on_delete=models.PROTECT, null=False, blank=False, verbose_name='Color')
    observacion = models.TextField(null=True, blank=True, verbose_name='Observaciones')
    establecimiento = models.ForeignKey('establecimientos.Establecimiento', on_delete=models.PROTECT, null=False,
                                        verbose_name='Establecimiento', related_name='sector_establecimiento')

    history = HistoricalRecords()

    def __str__(self):
        return self.color.nombre

    class Meta:
        verbose_name = 'Sector'
        verbose_name_plural = 'Sectores'
