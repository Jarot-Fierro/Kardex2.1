from django import forms

from core.validations import validate_exists
from personas.models.profesion import Profesion


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

        validate_exists(nombre, exists)

        return nombre

    class Meta:
        model = Profesion
        fields = ['nombre']
