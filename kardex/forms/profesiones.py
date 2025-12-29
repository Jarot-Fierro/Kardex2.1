from django import forms

from config.validations import validate_spaces, validate_exists
# from config.validation_forms import validate_name, validate_description, validate_spaces, validate_exists
from kardex.models import Profesion


class FormProfesion(forms.ModelForm):
    nombre = forms.CharField(
        label='Nombre de la profesion',
        widget=forms.TextInput(
            attrs={
                'id': 'nombre_profesion',
                'class': 'form-control',
                'placeholder': 'Ej: Medicina, Enfermería, etc...',
                'minlenght': '1',
                'maxlenght': '100'
            }),
        required=True
    )

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        current_instance = self.instance if self.instance.pk else None

        exists = Profesion.objects.filter(nombre__iexact=nombre).exclude(
            pk=current_instance.pk if current_instance else None).exists()

        validate_spaces(nombre)
        validate_exists(nombre, exists)

        return nombre

    class Meta:
        model = Profesion
        fields = ['nombre']
