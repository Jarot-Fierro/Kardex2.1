from django.db import models

from core.models import StandardModel


class MovimientoMonologoControlado(StandardModel):
    rut = models.CharField(max_length=50)
    numero_ficha = models.IntegerField()

    fecha_salida = models.DateTimeField(null=True, blank=True)
    usuario_entrega = models.CharField(max_length=50, blank=True, null=True)
    usuario_entrega_id = models.ForeignKey('personas.UsuarioAnterior', on_delete=models.PROTECT, null=True, blank=True,
                                           related_name='movimientos_entregados')

    fecha_entrada = models.DateTimeField(null=True, blank=True)
    usuario_entrada = models.CharField(max_length=50, null=True, blank=True)
    usuario_entrada_id = models.ForeignKey('personas.UsuarioAnterior', on_delete=models.PROTECT, null=True, blank=True,
                                           related_name='movimientos_recibidos')

    fecha_traspaso = models.DateTimeField(null=True, blank=True)
    usuario_traspaso = models.CharField(max_length=50, null=True, blank=True)

    observacion_salida = models.TextField(null=True, blank=True)
    observacion_entrada = models.TextField(null=True, blank=True)
    observacion_traspaso = models.TextField(null=True, blank=True)

    profesional = models.ForeignKey('personas.Profesional', on_delete=models.PROTECT, null=True, blank=True)
    profesional_anterior = models.CharField(max_length=50, null=True, blank=True)
    rut_paciente = models.ForeignKey('personas.Paciente', on_delete=models.PROTECT, null=True, blank=True)
    establecimiento = models.ForeignKey('establecimientos.Establecimiento', on_delete=models.PROTECT)
    ficha = models.ForeignKey('clinica.Ficha', on_delete=models.PROTECT, null=True, blank=True)
    servicio_clinico_destino = models.ForeignKey('establecimientos.ServicioClinico', on_delete=models.PROTECT,
                                                 null=True, blank=True)

    ESTADO_CHOICES = [
        ('E', 'Enviado'),
        ('R', 'Recibido'),
        ('S', 'Sin Paciente')
    ]

    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES)

    def __str__(self):
        return f'{self.establecimiento.nombre} - {self.rut_paciente} - {self.numero_ficha}'

    class Meta:
        verbose_name = 'Movimiento Monologo Controlado'
        verbose_name_plural = 'Movimientos Monologo Controlados'
        ordering = ['-fecha_salida']
