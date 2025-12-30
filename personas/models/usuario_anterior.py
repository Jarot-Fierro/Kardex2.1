from django.db import models
from simple_history.models import HistoricalRecords

from core.models import StandardModel
from establecimientos.models.establecimiento import Establecimiento


class UsuarioAnterior(StandardModel):
    rut = models.CharField(primary_key=True, max_length=100, unique=True, null=False, verbose_name='R.U.T.')
    nombre = models.CharField(max_length=100, null=False, verbose_name='Nombre')
    correo = models.EmailField(max_length=100, null=False, verbose_name='Correo')
    establecimiento = models.ForeignKey(Establecimiento, on_delete=models.PROTECT, null=True, blank=True,
                                        verbose_name='Establecimiento',
                                        related_name='usuarios_anteriores_establecimientos')
    history = HistoricalRecords()

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.upper()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Usuario Anterior'
        verbose_name_plural = 'Usuarios Anteriores'
