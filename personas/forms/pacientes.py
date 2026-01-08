from django import forms
from django.core.exceptions import ValidationError

from core.choices import ESTADO_CIVIL, SEXO_CHOICES
from core.validations import validate_rut, format_rut
from geografia.models.comuna import Comuna
from personas.models.genero import Genero
from personas.models.pacientes import Paciente
from personas.models.prevision import Prevision


class PacienteForm(forms.ModelForm):
    fecha_nacimiento = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control form-control-sm',
            'id': 'id_fecha_nacimiento',
            'name': 'fecha_nacimiento'
        })
    )

    fecha_fallecimiento = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control form-control-sm bg-danger text-white border-dange',
            'id': 'id_fecha_fallecimiento',
            'name': 'fecha_fallecimiento'
        })
    )

    rut = forms.CharField(
        label='R.U.T.',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Ingrese el RUT del paciente',
            'id': 'id_rut',
            'name': 'rut'
        }),
        required=True
    )

    nombre = forms.CharField(
        label='Nombres',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Ingrese el nombre del paciente',
            'id': 'id_nombre',
            'name': 'nombre'
        }),
        required=True
    )

    apellido_paterno = forms.CharField(
        label='Apellido Paterno',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'id': 'id_apellido_paterno',
            'name': 'apellido_paterno'
        }),
        required=True
    )

    apellido_materno = forms.CharField(
        label='Apellido Materno',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'id': 'id_apellido_materno',
            'name': 'apellido_materno'
        }),
        required=True
    )

    nombre_social = forms.CharField(
        label='Nombre Social',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'id': 'id_nombre_social',
            'name': 'nombre_social'
        }),
        required=False
    )

    pasaporte = forms.CharField(
        label='Pasaporte',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'id': 'id_pasaporte',
            'name': 'pasaporte'
        }),
        required=False
    )

    nip = forms.CharField(
        label='NIP',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'id': 'id_nie',
            'name': 'nip'
        }),
        required=False
    )

    sexo = forms.ChoiceField(
        choices=SEXO_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control form-control-sm',
            'id': 'id_sexo',
            'name': 'sexo'
        })
    )

    estado_civil = forms.ChoiceField(
        choices=ESTADO_CIVIL,
        widget=forms.Select(attrs={
            'class': 'form-control form-control-sm',
            'id': 'id_estado_civil',
            'name': 'estado_civil'
        })
    )

    recien_nacido = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_recien_nacido',
            'name': 'recien_nacido'
        })
    )

    extranjero = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_extranjero',
            'name': 'extranjero'
        })
    )

    pueblo_indigena = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_pueblo_indigena',
            'name': 'pueblo_indigena'
        })
    )

    fallecido = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_fallecido',
            'name': 'fallecido'
        })
    )

    usar_rut_madre_como_responsable = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_usar_rut_madre_como_responsable',
            'name': 'usar_rut_madre_como_responsable'
        })
    )

    sin_telefono = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_sin_telefono',
            'name': 'sin_telefono'
        })
    )

    rut_madre = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control form-control-sm', 'id': 'id_rut_madre', 'name': 'rut_madre'})
    )

    nombres_madre = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control form-control-sm', 'id': 'id_nombres_madre', 'name': 'nombres_madre'})
    )

    nombres_padre = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control form-control-sm', 'id': 'id_nombres_padre', 'name': 'nombres_padre'})
    )

    nombre_pareja = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control form-control-sm', 'id': 'id_nombre_pareja', 'name': 'nombre_pareja'})
    )

    representante_legal = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'id': 'id_representante_legal',
                                      'name': 'representante_legal'})
    )

    rut_responsable_temporal = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'id': 'id_rut_responsable_temporal',
                                      'name': 'rut_responsable_temporal'})
    )

    direccion = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control form-control-sm', 'id': 'id_direccion', 'name': 'direccion'})
    )

    numero_telefono1 = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control form-control-sm', 'id': 'id_numero_telefono1', 'name': 'numero_telefono1'})
    )

    numero_telefono2 = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control form-control-sm', 'id': 'id_numero_telefono2', 'name': 'numero_telefono2'})
    )

    ocupacion = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control form-control-sm', 'id': 'id_ocupacion', 'name': 'ocupacion'})
    )

    ## FOREINKEYS

    genero = forms.ModelChoiceField(
        label='Género',
        empty_label='Selecciona un Género',
        queryset=Genero.objects.filter(status=True),
        widget=forms.Select(attrs={'class': 'form-control form-control-sm', 'id': 'id_genero', 'name': 'genero'}),
    )

    prevision = forms.ModelChoiceField(
        label='Previsión',
        empty_label='Selecciona un Previsión',
        queryset=Prevision.objects.filter(status=True),
        widget=forms.Select(attrs={'class': 'form-control form-control-sm', 'id': 'id_prevision', 'name': 'prevision'}),
    )

    comuna = forms.ModelChoiceField(
        label='Comuna',
        empty_label='Selecciona un Comuna',
        queryset=Comuna.objects.filter(status=True),
        widget=forms.Select(attrs={'class': 'form-control form-control-sm', 'id': 'id_comuna', 'name': 'comuna'}),
    )

    class Meta:
        model = Paciente
        fields = [
            'rut', 'nombre', 'apellido_paterno', 'apellido_materno', 'nombre_social',
            'pasaporte', 'nip', 'sexo', 'genero', 'estado_civil',
            'recien_nacido', 'extranjero', 'pueblo_indigena', 'fallecido', 'fecha_fallecimiento',
            'rut_madre', 'nombres_madre', 'nombres_padre', 'nombre_pareja',
            'representante_legal', 'rut_responsable_temporal', 'usar_rut_madre_como_responsable',
            'direccion', 'comuna', 'ocupacion', 'numero_telefono1', 'numero_telefono2', 'sin_telefono'
        ]

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')

        if not rut:
            return rut

        rut_limpio = rut

        if not validate_rut(rut_limpio):
            raise ValidationError(f"El RUT ingresado no es válido.{validate_rut(rut_limpio)} {format_rut(rut_limpio)}")

        return format_rut(rut_limpio)
