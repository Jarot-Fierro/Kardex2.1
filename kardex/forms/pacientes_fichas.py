# usuarios.py
import datetime

from django import forms
from django.core.validators import RegexValidator

from kardex.choices import GENERO_CHOICES
from kardex.models import Prevision, Sector, Comuna


class PacienteForm(forms.Form):
    """
    Formulario para la creación/edición de pacientes
    """

    # =============================
    # 🔹 CAMPOS DEL ENCABEZADO
    # =============================

    rut = forms.CharField(
        label='R.U.T.',
        max_length=12,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control id_rut',
            'placeholder': '12.345.678-9',
            'id': 'id_rut'
        }),
        validators=[
            RegexValidator(
                regex=r'^(\d{1,3}(?:\.\d{3}){2}-[\dkK])$',
                message='Formato de RUT inválido. Use: 12.345.678-9'
            )
        ]
    )

    ficha = forms.CharField(
        label='N° FICHA',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'N° Ficha',
            'id': 'id_ficha',
        })
    )

    # =============================
    # 🔹 ESTADO DEL PACIENTE
    # =============================

    recien_nacido = forms.BooleanField(
        label='Recién Nacido',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'recien_nacido_paciente'
        })
    )

    extranjero = forms.BooleanField(
        label='Extranjero',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'extranjero_paciente'
        })
    )

    pueblo_indigena = forms.BooleanField(
        label='Pueblo Indígena',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'pueblo_indigena_paciente'
        })
    )

    fallecido = forms.BooleanField(
        label='Fallecido',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'fallecido_paciente'
        })
    )

    fecha_fallecimiento = forms.DateField(
        label='Fecha de Fallecimiento',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'fecha_fallecimiento_paciente'
        })
    )

    # =============================
    # 🔹 IDENTIFICACIÓN
    # =============================

    nombre = forms.CharField(
        label='Nombres',
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'nombre_paciente'
        })
    )

    apellido_paterno = forms.CharField(
        label='Apellido Paterno',
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'apellido_paterno_paciente'
        })
    )

    apellido_materno = forms.CharField(
        label='Apellido Materno',
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'apellido_materno_paciente'
        })
    )

    nombre_social = forms.CharField(
        label='Nombre Social',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'nombre_social_paciente'
        })
    )

    pasaporte = forms.CharField(
        label='Pasaporte',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'pasaporte_paciente'
        })
    )

    nie = forms.CharField(
        label='NIE',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'nie_paciente'
        })
    )

    # =============================
    # 🔹 DATOS DE NACIMIENTO
    # =============================

    fecha_nacimiento = forms.DateField(
        label='Fecha de Nacimiento',
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'fecha_nacimiento_paciente'
        })
    )

    SEXO_CHOICES = [
        ('', 'Seleccionar...'),
        ('NO INFORMADO', 'No Informado'),
        ('MASCULINO', 'Masculino'),
        ('FEMENINO', 'Femenino'),
    ]

    sexo = forms.ChoiceField(
        label='Sexo',
        choices=SEXO_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'sexo_paciente'
        })
    )

    genero = forms.ChoiceField(
        label='Género',
        choices=GENERO_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'genero_paciente'
        })
    )

    ESTADO_CIVIL_CHOICES = [
        ('', 'Seleccionar...'),
        ('NO INFORMADO', 'No Informado'),
        ('SOLTERO', 'Soltero'),
        ('CASADO', 'Casado'),
        ('DIVORCIADO', 'Divorciado'),
        ('VIUDO', 'Viudo'),
        ('SEPARADO', 'Separado'),
        ('CONVIVIENTE', 'Conviviente'),
    ]

    estado_civil = forms.ChoiceField(
        label='Estado Civil',
        choices=ESTADO_CIVIL_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'estado_civil_paciente'
        })
    )

    # =============================
    # 🔹 DATOS FAMILIARES
    # =============================

    rut_madre = forms.CharField(
        label='R.U.T. Madre',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control id_rut',
            'id': 'rut_madre_paciente'
        })
    )

    nombres_madre = forms.CharField(
        label='Nombres de la Madre',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'nombres_madre_paciente'
        })
    )

    nombres_padre = forms.CharField(
        label='Nombres del Padre',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'nombres_padre_paciente'
        })
    )

    nombre_pareja = forms.CharField(
        label='Nombre de la Pareja',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'nombre_pareja_paciente'
        })
    )

    representante_legal = forms.CharField(
        label='Representante Legal',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'representante_legal_paciente'
        })
    )

    rut_responsable_temporal = forms.CharField(
        label='RUT Responsable Temporal',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'rut_responsable_temporal_paciente'
        })
    )

    usar_rut_madre_como_responsable = forms.BooleanField(
        label='Usar RUT de la madre como responsable',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'usar_rut_madre_como_responsable_paciente'
        })
    )

    # =============================
    # 🔹 CONTACTO Y DIRECCIÓN
    # =============================

    direccion = forms.CharField(
        label='Dirección',
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'direccion_paciente'
        })
    )

    # Nota: Este campo se cargará dinámicamente desde la base de datos
    comuna = forms.ChoiceField(
        label='Comuna',
        choices=[('', 'Seleccionar comuna...')],
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'id': 'comuna_paciente'
        })
    )

    ocupacion = forms.CharField(
        label='Ocupación',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'ocupacion_paciente'
        })
    )

    sin_telefono = forms.BooleanField(
        label='Paciente Sin Teléfono',
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'sin_telefono'
        })
    )

    numero_telefono1 = forms.CharField(
        label='Número de Teléfono',
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'type': 'tel',
            'id': 'numero_telefono1_paciente'
        }),
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Formato de teléfono inválido'
            )
        ]
    )

    numero_telefono2 = forms.CharField(
        label='Número de Teléfono 2',
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'type': 'tel',
            'id': 'numero_telefono2_paciente'
        }),
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Formato de teléfono inválido'
            )
        ]
    )

    # =============================
    # 🔹 GESTIÓN
    # =============================

    # Nota: Este campo se cargará dinámicamente desde la base de datos
    prevision = forms.ModelChoiceField(
        label='Previsión',
        empty_label="Selecciona una Opción",
        queryset=Prevision.objects.all(),
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'prevision_paciente'
        })
    )

    # Nota: Este campo se cargará dinámicamente desde la base de datos
    sector = forms.ModelChoiceField(
        label='Sector',
        empty_label="Selecciona una Opción",
        queryset=Sector.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'sector_paciente'
        })
    )

    comuna = forms.ModelChoiceField(
        label='Comuna',
        empty_label="Selecciona una Opción",
        queryset=Comuna.objects.all(),
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'comuna_paciente'
        })
    )
    observacion = forms.CharField(
        label='Observación',
        widget=forms.Textarea(attrs={
            'id': 'observacion_paciente',
            'class': 'form-control',
            'placeholder': 'Ingrese una observación (opcional)',
            'rows': 3
        }),
        required=False
    )

    # =============================
    # 🔹 MÉTODOS DE VALIDACIÓN
    # =============================

    def clean(self):
        """Validaciones personalizadas del formulario"""
        cleaned_data = super().clean()

        # Validar que si es fallecido, tenga fecha de fallecimiento
        fallecido = cleaned_data.get('fallecido')
        fecha_fallecimiento = cleaned_data.get('fecha_fallecimiento')

        if fallecido and not fecha_fallecimiento:
            self.add_error('fecha_fallecimiento',
                           'Si el paciente es fallecido, debe ingresar la fecha de fallecimiento')

        # Validar que la fecha de fallecimiento no sea futura
        if fecha_fallecimiento and fecha_fallecimiento > datetime.date.today():
            self.add_error('fecha_fallecimiento',
                           'La fecha de fallecimiento no puede ser futura')

        # Validar que la fecha de nacimiento no sea futura
        fecha_nacimiento = cleaned_data.get('fecha_nacimiento')
        if fecha_nacimiento and fecha_nacimiento > datetime.date.today():
            self.add_error('fecha_nacimiento',
                           'La fecha de nacimiento no puede ser futura')

        # Validar que si es recién nacido, la fecha de nacimiento sea reciente
        if cleaned_data.get('recien_nacido') and fecha_nacimiento:
            dias_diferencia = (datetime.date.today() - fecha_nacimiento).days
            if dias_diferencia > 30:  # Más de 30 días no es "recién nacido"
                self.add_error('recien_nacido',
                               'Un paciente con más de 30 días no puede ser considerado recién nacido')

        # Validar relación entre teléfonos
        sin_telefono = cleaned_data.get('sin_telefono')
        telefono1 = cleaned_data.get('numero_telefono1')
        telefono2 = cleaned_data.get('numero_telefono2')

        if sin_telefono and (telefono1 or telefono2):
            self.add_error('sin_telefono',
                           'Si marca "Paciente Sin Teléfono", no puede ingresar números telefónicos')

        if not sin_telefono and not telefono1:
            self.add_error('numero_telefono1',
                           'Debe ingresar al menos un número de teléfono si no marca la opción "Sin Teléfono"')

        # Validar uso de RUT madre como responsable
        usar_rut_madre = cleaned_data.get('usar_rut_madre_como_responsable')
        rut_madre = cleaned_data.get('rut_madre')
        rut_responsable = cleaned_data.get('rut_responsable_temporal')

        if usar_rut_madre and not rut_madre:
            self.add_error('usar_rut_madre_como_responsable',
                           'Debe ingresar el RUT de la madre para usar como responsable')

        if usar_rut_madre and rut_responsable:
            self.add_error('rut_responsable_temporal',
                           'Si usa el RUT de la madre como responsable, no debe ingresar otro RUT responsable')

        return cleaned_data

    def clean_fecha_nacimiento(self):
        """Validación específica para fecha de nacimiento"""
        fecha = self.cleaned_data.get('fecha_nacimiento')

        if fecha:
            # Verificar que no sea mayor a 120 años
            edad_maxima = datetime.date.today() - datetime.timedelta(days=120 * 365)
            if fecha < edad_maxima:
                raise forms.ValidationError(
                    'La fecha de nacimiento no puede ser de hace más de 120 años'
                )

        return fecha

    def __init__(self, *args, **kwargs):
        """
        Inicialización del formulario para cargar opciones dinámicas
        """
        super().__init__(*args, **kwargs)

        # Aquí puedes cargar opciones dinámicas si es necesario
        # Por ejemplo:
        # from .models import Comuna, Prevision, Sector
        # self.fields['comuna'].choices = [('', 'Seleccionar...')] + [(c.id, c.nombre) for c in Comuna.objects.all()]
