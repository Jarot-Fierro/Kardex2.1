from django import forms

from core.validations import validate_exists
from personas.models.prevision import Prevision


class FormPrevision(forms.ModelForm):
    nombre = forms.CharField(
        label='Nombre de la Previsión',
        widget=forms.TextInput(
            attrs={
                'id': 'nombre_prevision',
                'class': 'form-control',
                'placeholder': 'Fonasa A, Isapre, etc...',
                'minlenght': '1',
                'maxlenght': '100'
            }),
        required=True
    )

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        current_instance = self.instance if self.instance.pk else None

        exists = Prevision.objects.filter(nombre__iexact=nombre).exclude(
            pk=current_instance.pk if current_instance else None).exists()

        validate_exists(nombre, exists)
        return nombre

    class Meta:
        model = Prevision
        fields = ['nombre']
