from django import forms
from django.core.exceptions import ValidationError

from core.validations import validate_rut, format_rut, validate_spaces, validate_email
from establecimientos.models.establecimiento import Establecimiento
from personas.models.profesion import Profesion
from personas.models.profesionales import Profesional


class FormProfesional(forms.ModelForm):
    rut = forms.CharField(
        label='R.U.T.',
        widget=forms.TextInput(attrs={
            'class': 'form-control id_rut',
            'placeholder': 'Ingrese el RUT del profesional',
        }),
        required=True
    )

    nombres = forms.CharField(
        label='Nombre',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el nombre del profesional',
            'id': 'nombres_profesional'
        }),
        required=True
    )

    correo = forms.EmailField(
        label='Correo Electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.cl',
            'id': 'correo_profesional'
        }),
        required=True
    )

    telefono = forms.CharField(
        label='Teléfono',
        widget=forms.TextInput(attrs={
            'class': 'form-control telefono_personal',
            'placeholder': '+569 1234 5678',
            'id': 'telefono_personal'
        }),
        required=False
    )

    anexo = forms.CharField(
        label='Anexo',
        widget=forms.TextInput(attrs={
            'class': 'form-control anexo_personal',
            'placeholder': '44 123 4567',
            'id': 'telefono_establecimiento'
        }),
        required=False
    )

    profesion = forms.ModelChoiceField(
        label='Profesión',
        queryset=Profesion.objects.filter(status=True),
        empty_label="Seleccione una Profesión",
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'id': 'profesion_profesional'
        }),
        required=False
    )

    establecimiento = forms.ModelChoiceField(
        label='Establecimiento',
        queryset=Establecimiento.objects.filter(status=True),
        empty_label='Seleccione un Establecimiento',
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'id': 'establecimiento_profesional'
        }),
        required=True
    )

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if not rut:
            return rut

        rut = rut.strip()

        # Validar que no contenga espacios
        if " " in rut:
            raise ValidationError("El RUT no debe contener espacios.")

        rut_sin_formato = rut.replace(".", "").replace("-", "").upper()

        if not validate_rut(rut_sin_formato):
            raise ValidationError("El RUT ingresado no es válido.")

        # Si ya existe otro profesional con el mismo RUT
        if Profesional.objects.filter(rut=format_rut(rut_sin_formato)).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Ya existe un profesional con este RUT.")

        return format_rut(rut_sin_formato)

    def clean_nombres(self):
        nombres = self.cleaned_data.get('nombres', '').strip()
        validate_spaces(nombres)
        return nombres

    def clean_correo(self):
        correo = self.cleaned_data.get('correo', '').strip()
        validate_email(correo)

        # Evitar correos duplicados
        if Profesional.objects.filter(correo=correo).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Ya existe un profesional con este correo electrónico.")
        return correo

    class Meta:
        model = Profesional
        fields = [
            'rut',
            'nombres',
            'correo',
            'telefono',
            'anexo',
            'profesion',
            'establecimiento'
        ]
