from django.db import models
from simple_history.models import HistoricalRecords

from config.abstract import StandardModel
from kardex.choices import ESTADO_CIVIL, GENERO_CHOICES


class Paciente(StandardModel):
    # IDENTIFICACIÓN
    codigo = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name='Código')
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
    genero = models.CharField(max_length=20, choices=GENERO_CHOICES, default='NO INFORMADO',
                              verbose_name='Estado Civil')

    # DATOS DE NACIMIENTO
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name='Fecha de Nacimiento')
    sexo = models.CharField(max_length=10, choices=[('MASCULINO', 'Masculino'), ('FEMENINO', 'Femenino')], null=False,
                            verbose_name='Sexo')
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

    comuna = models.ForeignKey('kardex.Comuna', on_delete=models.PROTECT, null=False,
                               verbose_name='Comuna', related_name='pacientes_comuna', default=1)
    prevision = models.ForeignKey('kardex.Prevision', on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name='Previsión', related_name='pacientes_prevision', default=1)

    usuario = models.ForeignKey('users.UsuarioPersonalizado', on_delete=models.SET_NULL, null=True, blank=True,
                                verbose_name='Usuario', related_name='pacientes_usuario')

    usuario_anterior = models.ForeignKey('kardex.UsuarioAnterior', on_delete=models.PROTECT, null=True, blank=True,
                                         verbose_name='UsuarioAnterior', related_name='usuarios_anteriores')

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.rut} - {self.nombre} {self.apellido_paterno} {self.apellido_materno}"

    class Meta:
        verbose_name = 'Paciente'
        verbose_name_plural = 'Pacientes'

    def save(self, *args, **kwargs):
        # Normalizar campos texto
        if self.rut:
            self.rut = self.rut.strip().lower()
        if self.nip:
            self.nip = self.nip.strip().upper()
        if self.nombre:
            self.nombre = self.nombre.strip().upper()
        if self.rut_madre:
            self.rut_madre = self.rut_madre.strip().upper()
        if self.apellido_paterno:
            self.apellido_paterno = self.apellido_paterno.strip().upper()
        if self.apellido_materno:
            self.apellido_materno = self.apellido_materno.strip().upper()
        if self.rut_responsable_temporal:
            self.rut_responsable_temporal = self.rut_responsable_temporal.strip().upper()
        if self.pasaporte:
            self.pasaporte = self.pasaporte.strip().upper()
        if self.nombre_social:
            self.nombre_social = self.nombre_social.strip().upper()
        if self.genero:
            self.genero = self.genero.strip().upper()
        if self.estado_civil:
            self.estado_civil = self.estado_civil.strip().upper()
        if self.nombres_padre:
            self.nombres_padre = self.nombres_padre.strip().upper()
        if self.nombres_madre:
            self.nombres_madre = self.nombres_madre.strip().upper()
        if self.nombre_pareja:
            self.nombre_pareja = self.nombre_pareja.strip().upper()
        if self.representante_legal:
            self.representante_legal = self.representante_legal.strip().upper()
        if self.direccion:
            self.direccion = self.direccion.strip().upper()
        if self.numero_telefono1:
            self.numero_telefono1 = self.numero_telefono1.strip()
        if self.numero_telefono2:
            self.numero_telefono2 = self.numero_telefono2.strip()
        if self.ocupacion:
            self.ocupacion = self.ocupacion.strip().upper()
        if self.alergico_a:
            self.alergico_a = self.alergico_a.strip().upper()

        # Si es creación y no tiene código, hacer primer save sin historial para obtener el ID
        is_creating = self.pk is None
        if is_creating and not self.codigo:
            # deshabilitar historial para este primer guardado
            setattr(self, '_disable_history', True)
            super().save(*args, **kwargs)
            # limpiar flag para que el próximo guardado sí cree historial
            if hasattr(self, '_disable_history'):
                delattr(self, '_disable_history')

            # generar y asignar código basado en el ID
            self.codigo = f"PAC-{self.pk:07d}"
            # ahora guardar normalmente (esto creará un único registro en el historial con el código)
            super().save(update_fields=["codigo"])  # no usar signals, ni crear segundo historial previo
            return

        # Comportamiento normal para updates o creaciones con código previamente definido
        super().save(*args, **kwargs)
