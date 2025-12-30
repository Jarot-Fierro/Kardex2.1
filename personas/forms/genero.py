from django import forms

from core.validations import validate_exists
from personas.models.genero import Genero


class FormGenero(forms.ModelForm):
    nombre = forms.CharField(
        label='Nombre del Género',
        widget=forms.TextInput(
            attrs={
                'id': 'nombre_pais',
                'class': 'form-control',
                'placeholder': 'Género',
                'minlenght': '1',
                'maxlenght': '100'
            }),
        required=True
    )

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        current_instance = self.instance if self.instance.pk else None

        exists = Genero.objects.filter(nombre__iexact=nombre).exclude(
            pk=current_instance.pk if current_instance else None).exists()

        validate_exists(nombre, exists)
        return nombre

    class Meta:
        model = Genero
        fields = ['nombre', ]
