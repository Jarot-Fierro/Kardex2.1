from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from config.abstract import StandardModel
from kardex.choices import ESTADO_RESPUESTA


class MovimientoFicha(StandardModel):
    fecha_envio = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Envío')
    fecha_recepcion = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Recepción')
    fecha_traspaso = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Traspaso')

    observacion_envio = models.TextField(null=True, blank=True, verbose_name='Observación de Envío')
    observacion_recepcion = models.TextField(null=True, blank=True, verbose_name='Observación de Recepción')
    observacion_traspaso = models.TextField(null=True, blank=True, verbose_name='Observación de Traspaso')

    estado_envio = models.CharField(max_length=50, choices=ESTADO_RESPUESTA,
                                    default='ENVIADO', null=True, blank=True, verbose_name='Estado de Envío')

    estado_recepcion = models.CharField(max_length=50, choices=ESTADO_RESPUESTA,
                                        default='EN ESPERA', null=True, blank=True, verbose_name='Estado de Recepción')

    estado_traspaso = models.CharField(max_length=50, choices=ESTADO_RESPUESTA,
                                       default='SIN TRASPASO', null=True, blank=True, verbose_name='Estado de Traspaso')

    servicio_clinico_envio = models.ForeignKey('kardex.ServicioClinico', on_delete=models.PROTECT,
                                               verbose_name='Servicio Clínico de Envío',
                                               related_name='envios_desde_este_servicio',
                                               null=True, blank=True,
                                               )

    servicio_clinico_recepcion = models.ForeignKey('kardex.ServicioClinico', on_delete=models.PROTECT,
                                                   verbose_name='Servicio Clínico de Recepción',
                                                   related_name='recepciones_en_este_servicio',
                                                   null=True, blank=True,
                                                   )

    servicio_clinico_traspaso = models.ForeignKey('kardex.ServicioClinico', on_delete=models.PROTECT,
                                                  verbose_name='Servicio Clínico de Traspaso',
                                                  related_name='traspaso_en_este_servicio',
                                                  null=True, blank=True,
                                                  )
    usuario_envio = models.ForeignKey('users.UsuarioPersonalizado', null=True, blank=True, on_delete=models.PROTECT,
                                      verbose_name='Usuario Envio', related_name='movimientos_enviados',
                                      )

    usuario_recepcion = models.ForeignKey('users.UsuarioPersonalizado', null=True, blank=True,
                                          on_delete=models.PROTECT,
                                          verbose_name='Usuario Recepcion', related_name='movimientos_recepcionados',
                                          )

    usuario_traspaso = models.ForeignKey('users.UsuarioPersonalizado', null=True, blank=True,
                                         on_delete=models.PROTECT,
                                         verbose_name='Usuario Traspaso', related_name='movimientos_traspasados',
                                         )

    usuario_envio_anterior = models.ForeignKey('kardex.UsuarioAnterior', null=True, blank=True,
                                               on_delete=models.PROTECT,
                                               verbose_name='Usuario Envio Anterior',
                                               related_name='movimientos_enviados_anterior',
                                               )

    usuario_recepcion_anterior = models.ForeignKey('kardex.UsuarioAnterior', null=True, blank=True,
                                                   on_delete=models.PROTECT,
                                                   verbose_name='Usuario Recepcion Anterior',
                                                   related_name='movimientos_recepcionados_anterior',
                                                   )

    profesional_envio = models.ForeignKey('kardex.Profesional', null=True, blank=True, on_delete=models.PROTECT,
                                          verbose_name='Profesional Envio',
                                          related_name='movimientos_enviados_profesionales',
                                          )

    profesional_recepcion = models.ForeignKey('kardex.Profesional', null=True, blank=True, on_delete=models.PROTECT,
                                              verbose_name='Profesional Recepcion',
                                              related_name='movimientos_recepcionados_profesionales',
                                              )

    profesional_traspaso = models.ForeignKey('kardex.Profesional', null=True, blank=True, on_delete=models.PROTECT,
                                             verbose_name='Profesional Recepcion',
                                             related_name='movimientos_traspaso_profesionales',
                                             )

    establecimiento = models.ForeignKey('kardex.Establecimiento', on_delete=models.PROTECT, null=True, blank=True,
                                        verbose_name='Establecimiento',
                                        related_name='movimientos_fichas_establecimientos')

    rut_anterior = models.CharField(max_length=50, default='SIN RUT', null=True, blank=True,
                                    verbose_name='RUT Anterior del Usuario')

    rut_anterior_profesional = models.CharField(max_length=50, default='SIN RUT', null=True, blank=True,
                                                verbose_name='RUT Anterior del Profesional')

    ficha = models.ForeignKey('kardex.Ficha', null=True, blank=True, on_delete=models.PROTECT,
                              verbose_name='Ficha')

    history = HistoricalRecords()

    def clean(self):
        # servicios distintos
        if self.servicio_clinico_envio_id and self.servicio_clinico_recepcion_id and \
                self.servicio_clinico_envio_id == self.servicio_clinico_recepcion_id:
            raise ValidationError(
                {'servicio_clinico_recepcion': 'El servicio de recepción no puede ser igual al de envío.'})
        # no editar si ya está recibido
        if self.pk and self.estado_recepcion == 'RECIBIDO':
            # Permitir idempotencia al marcar recibido: si lo único que cambia es establecer precisamente
            # los campos de recepción desde vacío a sus valores definitivos, no bloquear.
            changed = []
            try:
                old = type(self).objects.get(pk=self.pk)
                tracked = ['fecha_envio', 'observacion_envio', 'estado_envio', 'servicio_clinico_envio',
                           'usuario_envio', 'profesional_envio',
                           'ficha', 'servicio_clinico_recepcion', 'observacion_recepcion', 'profesional_recepcion',
                           'fecha_recepcion', 'estado_recepcion', 'usuario_recepcion']
                for f in tracked:
                    if getattr(old, f) != getattr(self, f):
                        changed.append(f)
            except type(self).DoesNotExist:
                pass

    def save(self, *args, **kwargs):
        creating = self.pk is None

        # Si es un movimiento nuevo (creación)
        if creating:
            # Si no tiene estado de envío, lo marcamos como ENVIADO
            if not self.estado_envio:
                self.estado_envio = 'ENVIADO'
            # Si no tiene estado de recepción, queda en espera
            if not self.estado_recepcion:
                self.estado_recepcion = 'EN ESPERA'
            # Si no tiene estado de traspaso, también en espera
            if not self.estado_traspaso:
                self.estado_traspaso = 'EN ESPERA'
            # Asignamos la fecha de envío automáticamente
            if not self.fecha_envio:
                self.fecha_envio = timezone.now()

        else:
            # Si se marca como recibido y no tiene fecha, se asigna automáticamente
            if self.estado_recepcion == 'RECIBIDO' and not self.fecha_recepcion:
                self.fecha_recepcion = timezone.now()

            # Si se marca como traspasado y no tiene fecha, también se asigna
            if self.estado_traspaso == 'TRASPASADO' and not self.fecha_traspaso:
                self.fecha_traspaso = timezone.now()

        # Validación de datos antes de guardar
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Movimiento de Ficha #{self.ficha.numero_ficha_sistema if self.ficha else 'N/A'}"

    class Meta:
        verbose_name = 'Movimiento Ficha'
        verbose_name_plural = 'Movimientos Fichas'
