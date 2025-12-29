from django.contrib.auth.models import AbstractUser
from django.db import models
from simple_history.models import HistoricalRecords


class User(AbstractUser):
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=200, unique=True)
    password = models.CharField(max_length=128)
    establecimiento = models.ForeignKey('establecimientos.Establecimiento', on_delete=models.PROTECT, null=True,
                                        blank=True,
                                        verbose_name='Establecimiento'
                                        )

    history = HistoricalRecords()

    USERNAME_FIELD = 'username'

    def save(self, *args, **kwargs):
        if self.username:
            self.username = self.username.upper()

        if self.first_name:
            self.first_name = self.first_name.upper()

        if self.last_name:
            self.last_name = self.last_name.upper()

        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'users'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.username


class Role(models.Model):
    rol_id = models.AutoField(primary_key=True)
    PERMISSION_CHOICES = [
        (0, 'Sin acceso'),
        (1, 'Solo lectura'),
        (2, 'Lectura y escritura'),
    ]

    role_name = models.CharField(max_length=50, unique=True)
    comunas = models.IntegerField(choices=PERMISSION_CHOICES, default=0)
    establecimientos = models.IntegerField(choices=PERMISSION_CHOICES, default=0)
    fichas = models.IntegerField(choices=PERMISSION_CHOICES, default=0)
    genero = models.IntegerField(choices=PERMISSION_CHOICES, default=0)
    movimiento_ficha = models.IntegerField(choices=PERMISSION_CHOICES, default=0)
    paciente = models.IntegerField(choices=PERMISSION_CHOICES, default=0)
    pais = models.IntegerField(choices=PERMISSION_CHOICES, default=0)
    prevision = models.IntegerField(choices=PERMISSION_CHOICES, default=0)
    profesion = models.IntegerField(choices=PERMISSION_CHOICES, default=0)
    profesionales = models.IntegerField(choices=PERMISSION_CHOICES, default=0)
    sectores = models.IntegerField(choices=PERMISSION_CHOICES, default=0)
    servicio_clinico = models.IntegerField(choices=PERMISSION_CHOICES, default=0)
    reportes = models.IntegerField(choices=PERMISSION_CHOICES, default=0)
    soporte = models.IntegerField(choices=PERMISSION_CHOICES, default=0)

    history = HistoricalRecords()

    class Meta:
        db_table = 'roles'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.role_name


class UserRole(models.Model):
    user_role_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    role_id = models.ForeignKey(Role, on_delete=models.CASCADE)

    history = HistoricalRecords()

    class Meta:
        db_table = 'user_roles'
        verbose_name = 'Rol del Usuario'
        verbose_name_plural = 'Roles del Usuario'
        unique_together = ('user_id', 'role_id')

    def __str__(self):
        return self.user_id.username
