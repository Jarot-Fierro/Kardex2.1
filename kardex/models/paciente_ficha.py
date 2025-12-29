from django.db import models


class VistaFichaPaciente(models.Model):
    # -------- FICHA -------
    ficha_id = models.IntegerField(primary_key=True)
    numero_ficha_sistema = models.IntegerField()
    numero_ficha_tarjeta = models.IntegerField(null=True)
    pasivado = models.BooleanField()
    observacion = models.TextField(null=True)
    fecha_creacion_anterior = models.DateTimeField(null=True)

    sector_id = models.IntegerField(null=True)
    usuario_id = models.IntegerField(null=True)

    # -------- ESTABLECIMIENTO -------
    establecimiento_id = models.IntegerField()
    establecimiento_nombre = models.CharField(max_length=100)
    establecimiento_direccion = models.CharField(max_length=200)
    establecimiento_telefono = models.CharField(max_length=15)
    establecimiento_comuna_id = models.IntegerField()

    # -------- PACIENTE -------
    paciente_id = models.IntegerField()
    paciente_codigo = models.CharField(max_length=100)
    rut = models.CharField(max_length=100)
    nip = models.CharField(max_length=100, null=True)
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=100)
    apellido_materno = models.CharField(max_length=100)

    nombre_social = models.CharField(max_length=100, null=True)
    genero = models.CharField(max_length=20)

    fecha_nacimiento = models.DateField(null=True)
    sexo = models.CharField(max_length=10)
    estado_civil = models.CharField(max_length=20)

    rut_madre = models.CharField(max_length=100, null=True)
    nombres_padre = models.CharField(max_length=100, null=True)
    nombres_madre = models.CharField(max_length=100, null=True)
    nombre_pareja = models.CharField(max_length=100, null=True)
    representante_legal = models.CharField(max_length=100, null=True)

    pueblo_indigena = models.BooleanField()
    recien_nacido = models.BooleanField()
    extranjero = models.BooleanField()
    fallecido = models.BooleanField()

    fecha_fallecimiento = models.DateField(null=True)
    alergico_a = models.CharField(max_length=200, null=True)

    direccion = models.CharField(max_length=200, null=True)
    sin_telefono = models.BooleanField()
    numero_telefono1 = models.CharField(max_length=15, null=True)
    numero_telefono2 = models.CharField(max_length=15, null=True)
    ocupacion = models.CharField(max_length=100, null=True)

    paciente_comuna_id = models.IntegerField()
    prevision_id = models.IntegerField(null=True)

    paciente_usuario_id = models.IntegerField(null=True)
    usuario_anterior_id = models.IntegerField(null=True)

    pasaporte = models.CharField(max_length=50, null=True)
    rut_responsable_temporal = models.CharField(max_length=100, null=True)
    usar_rut_madre_como_responsable = models.BooleanField()

    class Meta:
        managed = False
        db_table = "vista_ficha_paciente"
