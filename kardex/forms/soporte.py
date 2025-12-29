# kardex/forms.py

# kardex/forms.py

# kardex/forms.py

from django import forms

from kardex.models import Soporte


class SoporteForm(forms.ModelForm):
    class Meta:
        model = Soporte
        fields = [
            'titulo',
            'descripcion',
            'categoria',
            'prioridad',
        ]

        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Asunto del problema'
            }),

            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe detalladamente tu problema'
            }),

            'categoria': forms.Select(attrs={
                'class': 'form-control'
            }),

            'prioridad': forms.Select(attrs={
                'class': 'form-control'
            }),

        }
