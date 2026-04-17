from django.db import models

from core.choices import SEXO_CHOICES, ESTADO_CIVIL
from core.models import StandardModel


class RespaldoPaciente(StandardModel):
    # IDENTIFICACIÓN
    ficha = models.CharField(max_length=100, null=True, blank=True, verbose_name='Numero de Ficha/Antes de Borrar')
    codigo = models.CharField(max_length=100,null=True, blank=True, verbose_name='Código')
    id_anterior = models.IntegerField(null=True, blank=True, verbose_name='ID Anterior')
    rut = models.CharField(max_length=100, null=True, blank=True, verbose_name='R.U.T.')
    nip = models.CharField(max_length=100, null=True, blank=True, verbose_name='NIP')
    nombre = models.CharField(max_length=100, null=False, verbose_name='Nombre')
    rut_madre = models.CharField(max_length=100, null=True, blank=True, verbose_name='R.U.T. Madre')
    apellido_paterno = models.CharField(max_length=100, null=False, verbose_name='Apellido Paterno')
    apellido_materno = models.CharField(max_length=100, null=False, verbose_name='Apellido Materno')
    pueblo_indigena = models.BooleanField(default=False, verbose_name='Pueblo Indigena')

    rut_responsable_temporal = models.CharField(max_length=100, null=True, blank=True,
                                                verbose_name='RUT Responsable Temporal'
                                                )

    usar_rut_madre_como_responsable = models.BooleanField(default=False,
                                                          verbose_name='Usar RUT de la madre como responsable'
                                                          )

    pasaporte = models.CharField(max_length=50, null=True, blank=True, verbose_name='Pasaporte')
    nombre_social = models.CharField(max_length=100, null=True, blank=True, verbose_name='Nombre Social')

    # DATOS DE NACIMIENTO
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name='Fecha de Nacimiento')
    sexo = models.CharField(max_length=50, choices=SEXO_CHOICES, null=False,
                            verbose_name='Sexo', default='NO INFORMADO')
    estado_civil = models.CharField(max_length=20, choices=ESTADO_CIVIL, null=False, verbose_name='Estado Civil',
                                    default='NO INFORMADO')

    # DATOS FAMILIARES
    nombres_padre = models.CharField(max_length=100, verbose_name='Nombres del Padre', null=True, blank=True)
    nombres_madre = models.CharField(max_length=100, verbose_name='Nombres de la Madre', null=True, blank=True)
    nombre_pareja = models.CharField(max_length=100, verbose_name='Nombre de la Pareja', null=True, blank=True)
    representante_legal = models.CharField(max_length=100, null=True, blank=True, verbose_name='Representante Legal')

    # CONTACTO Y DIRECCIÓN
    direccion = models.CharField(max_length=200, verbose_name='Dirección', null=True, blank=True)
    sin_telefono = models.BooleanField(default=False)
    numero_telefono1 = models.CharField(max_length=15, verbose_name='Número de Teléfono', null=True, blank=True)
    numero_telefono2 = models.CharField(max_length=15, verbose_name='Número de Teléfono 2', null=True, blank=True)
    ocupacion = models.CharField(max_length=100, null=True, blank=True, verbose_name='Ocupación')

    # ESTADO DEL PACIENTE
    recien_nacido = models.BooleanField(default=False, verbose_name='Recién Nacido')
    extranjero = models.BooleanField(default=False, verbose_name='Extranjero')
    fallecido = models.BooleanField(default=False, verbose_name='Fallecido')
    fecha_fallecimiento = models.DateField(null=True, blank=True, verbose_name='Fecha de Fallecimiento')
    alergico_a = models.CharField(null=True, blank=True, max_length=200, verbose_name='Alergico a')

    comuna = models.ForeignKey('geografia.Comuna', on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name='Comuna', related_name='respaldo_pacientes_comuna', default=1)
    prevision = models.ForeignKey('personas.Prevision', on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name='Previsión', related_name='respaldo_pacientes_prevision', default=1)

    genero = models.ForeignKey('personas.Genero', on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name='Género',
                               related_name='respaldo_pacientes_genero')

    usuario = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True,
                                verbose_name='Usuario', related_name='respaldo_pacientes_usuario')

    usuario_anterior = models.ForeignKey('personas.UsuarioAnterior', on_delete=models.SET_NULL, null=True, blank=True,
                                         verbose_name='UsuarioAnterior', related_name='respaldo_usuarios_anteriores')

    # Auditoria de eliminación
    usuario_eliminacion = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True,
                                            verbose_name='Usuario responsable de la eliminación',
                                            related_name='respaldo_respaldo_pacientes_eliminados')
    motivo_eliminacion = models.TextField(null=True, blank=True, verbose_name='Motivo de la eliminación')

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido_paterno} {self.apellido_materno}".strip()

    def __str__(self):
        return f"{self.rut} - {self.nombre_completo}"