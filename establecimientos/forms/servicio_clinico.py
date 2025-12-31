from django import forms

from core.validations import validate_exists
from establecimientos.models.servicio_clinico import ServicioClinico


class FormServicioClinico(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        # Capturamos request para usar el establecimiento del usuario
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

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
            'class': 'form-control',
            'placeholder': '(Opcional)',
            'id': 'telefono_servicioclinico'
        }),
        required=False
    )

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()

        # Obtenemos el establecimiento del usuario logueado
        establecimiento = (
            getattr(self.request.user, 'establecimiento', None)
            if self.request else None
        )

        if not establecimiento:
            raise forms.ValidationError("No tienes un establecimiento asignado.")

        current_instance = self.instance if self.instance.pk else None

        exists = ServicioClinico.objects.filter(
            nombre__iexact=nombre,
            establecimiento=establecimiento
        ).exclude(
            pk=current_instance.pk if current_instance else None
        ).exists()

        # Utilizas tu validador personalizado
        validate_exists(nombre, exists)

        return nombre

    class Meta:
        model = ServicioClinico
        fields = ['nombre', 'correo_jefe', 'telefono']
