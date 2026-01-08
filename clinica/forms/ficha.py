from django import forms

from clinica.models import Ficha
from establecimientos.models.sectores import Sector


class FichaForm(forms.ModelForm):
    numero_ficha_sistema = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm',
            'id': 'id_ficha',
            'name': 'ficha',
            'placeholder': 'Número de ficha sistema'
        })
    )

    pasivado = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_pasivado',
            'name': 'pasivado'
        })
    )

    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-sm',
            'id': 'id_observacion',
            'name': 'observacion',
            'rows': 3,
            'placeholder': 'Observaciones de la ficha'
        })
    )

    sector = forms.ModelChoiceField(
        queryset=Sector.objects.filter(status=True),
        required=False,
        empty_label='Selecciona un Sector',
        widget=forms.Select(attrs={
            'class': 'form-control form-control-sm',
            'id': 'id_sector',
            'name': 'sector'
        })
    )

    class Meta:
        model = Ficha
        fields = [
            'numero_ficha_sistema', 'pasivado', 'observacion',
            'fecha_creacion_anterior', 'paciente', 'sector',
        ]
