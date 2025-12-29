from django.db import models

from config import settings


class StandardModel(models.Model):
    STATUS_CHOICES = [
        (True, 'Activo'),
        (False, 'Inactivo'),
    ]
    status = models.BooleanField(default=True, choices=STATUS_CHOICES, verbose_name='Estado')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha Creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última Actualización')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="%(class)s_created", verbose_name='Creado Por')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="%(class)s_updated", verbose_name='Actualizado Por')

    class Meta:
        abstract = True
        ordering = ['-updated_at']
