from django import forms

from establecimientos.models.establecimiento import Establecimiento
from establecimientos.models.servicio_clinico import ServicioClinico


class FormServicioClinico(forms.ModelForm):
    nombre = forms.CharField(
        label='Nombre del Servicio',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Urgencias, Pediatría, etc.',
            'id': 'nombre_servicioclinico'
        }),
        required=True
    )

    correo_jefe = forms.EmailField(
        label='Correo del Jefe a Cargo',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.cl',
            'id': 'correo_jefe_servicioclinico'
        }),
        required=False
    )

    telefono = forms.CharField(
        label='Teléfono',
        widget=forms.TextInput(attrs={
            'class': 'form-control telefono_personal',
            'placeholder': '+56912345678',
            'id': 'telefono_servicioclinico'
        }),
        required=False
    )

    establecimiento = forms.ModelChoiceField(
        label='Establecimiento',
        empty_label='Seleccione un Establecimiento',
        queryset=Establecimiento.objects.filter(status=True),
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'id': 'establecimiento_servicioclinico'
        }),
        required=True
    )

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        current_instance = self.instance if self.instance.pk else None

        exists = ServicioClinico.objects.filter(nombre__iexact=nombre).exclude(
            pk=current_instance.pk if current_instance else None).exists()

        return nombre

    class Meta:
        model = ServicioClinico
        fields = [
            'nombre',
            'establecimiento',
            'correo_jefe',
            'telefono',
        ]
