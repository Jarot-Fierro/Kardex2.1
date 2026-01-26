from django.db import models
from simple_history.models import HistoricalRecords

from core.models import StandardModel
from establecimientos.models.establecimiento import Establecimiento
from personas.models.profesion import Profesion


class Profesional(StandardModel):
    rut = models.CharField(max_length=100, null=False, verbose_name='R.U.T.')
    nombres = models.CharField(max_length=100, null=False, verbose_name='Nombre')
    correo = models.EmailField(max_length=100, null=False, verbose_name='Correo')
    telefono = models.CharField(max_length=50, null=True, blank=True, verbose_name='Teléfono')
    anexo = models.CharField(max_length=15, null=True, blank=True, verbose_name='Anexo')
    profesion = models.ForeignKey(Profesion, null=True, blank=True, on_delete=models.SET_NULL,
                                  verbose_name='Profesión', related_name='profesionales_profesion')

    establecimiento = models.ForeignKey(Establecimiento, null=True, blank=True, on_delete=models.SET_NULL,
                                        verbose_name='Establecimiento', related_name='profesionales_establecimiento')

    history = HistoricalRecords()

    def __str__(self):
        return self.nombres

    def save(self, *args, **kwargs):
        if self.rut:
            self.rut = self.rut.upper()
        if self.nombres:
            self.nombres = self.nombres.upper()
        if self.correo:
            self.correo = self.correo.lower()

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Profesional'
        verbose_name_plural = 'Profesionales'
