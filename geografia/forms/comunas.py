from django import forms

from core.validations import validate_exists
from geografia.models.comuna import Comuna


# from config.validation_forms import validate_name, validate_description, validate_spaces, validate_exists


class FormComuna(forms.ModelForm):
    nombre = forms.CharField(
        label='Nombre de la comuna',
        widget=forms.TextInput(
            attrs={
                'id': 'nombre_comuna',
                'class': 'form-control',
                'placeholder': 'Lebu',
                'minlenght': '1',
                'maxlenght': '100'
            }),
        required=True
    )
    codigo = forms.CharField(
        label='Código de Comuna',
        widget=forms.TextInput(
            attrs={
                'id': 'codigo_comuna',
                'class': 'form-control',
                'placeholder': '1132',
                'minlenght': '1',
                'maxlenght': '100'
            }),
        required=False
    )

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        current_instance = self.instance if self.instance.pk else None

        exists = Comuna.objects.filter(nombre__iexact=nombre).exclude(
            pk=current_instance.pk if current_instance else None).exists()

        validate_exists(nombre, exists)
        return nombre

    class Meta:
        model = Comuna
        fields = ['nombre', 'codigo']
