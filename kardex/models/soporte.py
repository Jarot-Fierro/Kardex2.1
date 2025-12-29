import os
import uuid
from datetime import datetime

from django.db import models
from simple_history.models import HistoricalRecords

from config.abstract import StandardModel


def soporte_upload_path(instance, filename):
    """
    Genera el path para adjuntos de soportes:
    formato: DD_MM_YYYY_UUID6_nombreoriginal.ext
    """
    fecha = datetime.now().strftime("%d_%m_%Y")
    uuid6 = str(uuid.uuid4())[:6]
    base, ext = os.path.splitext(filename)
    nuevo_nombre = f"{fecha}_{uuid6}_{base}{ext}"
    return os.path.join("soportes", nuevo_nombre)


class Soporte(StandardModel):
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]

    ESTADO_CHOICES = [
        ('abierto', 'Abierto'),
        ('proceso', 'En proceso'),
        ('espera', 'En espera'),
        ('resuelto', 'Resuelto'),
        ('cerrado', 'Cerrado'),
    ]

    CATEGORIA_CHOICES = [
        ('sistema', 'Sistema'),
        ('hardware', 'Hardware'),
        ('red', 'Red / Conectividad'),
        ('usuario', 'Usuario / Accesos'),
        ('otro', 'Otro'),
    ]

    titulo = models.CharField(max_length=150)
    descripcion = models.TextField()
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='otro')
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='media')
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='abierto')

    creado_por = models.ForeignKey(
        'users.UsuarioPersonalizado',
        on_delete=models.SET_NULL,
        null=True,
        related_name="soportes_creados"
    )

    establecimiento = models.ForeignKey(
        'kardex.Establecimiento',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Establecimiento'
    )

    fecha_cierre = models.DateTimeField(null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.id} | {self.titulo}"
