from django.db import models

from core.models import StandardModel


class RespaldoFicha(StandardModel):
    numero_ficha_sistema = models.IntegerField(null=True, blank=True, verbose_name='Número de Ficha')
    numero_ficha_tarjeta = models.IntegerField(null=True, blank=True,
                                               verbose_name='Número de Ficha Tarjeta')
    numero_ficha_respaldo = models.IntegerField(null=True, blank=True,
                                                verbose_name='Número de Ficha Respaldo')
    rut = models.CharField(max_length=50, null=True, blank=True,
                                    verbose_name='RUT del Usuario/Antes de Borrar')
    pasivado = models.BooleanField(default=False, verbose_name='Pasivado')
    observacion = models.TextField(null=True, blank=True, verbose_name='Observación')

    usuario = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True, blank=True,
                                verbose_name='Usuario', related_name='respaldo_fichas_usuarios')

    usuario_anterior = models.ForeignKey('personas.UsuarioAnterior', on_delete=models.PROTECT, null=True, blank=True,
                                         verbose_name='Usuario Anterior', related_name='respaldo_fichas_usuarios_anteriores')

    rut_anterior = models.CharField(max_length=50, null=True, blank=True,
                                    verbose_name='RUT Anterior del Usuario')

    fecha_creacion_anterior = models.DateTimeField(null=True, blank=True)

    paciente = models.ForeignKey('personas.Paciente', on_delete=models.PROTECT, null=True, blank=True,
                                 verbose_name='Paciente', related_name='respaldo_fichas_pacientes')

    fecha_mov = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Movimiento')

    establecimiento = models.ForeignKey('establecimientos.Establecimiento', on_delete=models.PROTECT, null=True,
                                        blank=True,
                                        verbose_name='Establecimiento', related_name='respaldo_fichas_establecimientos')

    sector = models.ForeignKey('establecimientos.Sector', on_delete=models.PROTECT, null=True, blank=True,
                               verbose_name='Sector', related_name='respaldo_fichas_sectores')

    # Auditoria de eliminación
    usuario_eliminacion = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True,
                                            verbose_name='Usuario responsable de la eliminación',
                                            related_name='respaldo_respaldo_fichas_eliminadas')
    motivo_eliminacion = models.TextField(null=True, blank=True, verbose_name='Motivo de la eliminación')


    def __str__(self):
        num = self.numero_ficha_sistema

        numero = f"{num:04d}" if num is not None else "----"

        if self.paciente:
            nombre_completo = self.paciente.nombre_completo
            if nombre_completo:
                return f"Ficha #{numero} - {nombre_completo}"
            else:
                return f"Ficha #{numero} - Código paciente: {self.paciente.codigo or '----'}"
        else:
            return f"Ficha #{numero} - Sin paciente"


    class Meta:
        verbose_name = 'Respaldo de Ficha'
        verbose_name_plural = 'Respaldo de Fichas'
