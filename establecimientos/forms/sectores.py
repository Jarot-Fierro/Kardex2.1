from django import forms

from establecimientos.models.colores import Color
from establecimientos.models.establecimiento import Establecimiento
from establecimientos.models.sectores import Sector


class FormSector(forms.ModelForm):
    codigo = forms.CharField(
        label='Código o Nombre del Sector',
        widget=forms.TextInput(
            attrs={
                'id': 'nombre_sector',
                'class': 'form-control',
                'placeholder': '(Opcional)',
                'minlenght': '1',
                'maxlenght': '100'
            }),
        required=False
    )
    color = forms.ModelChoiceField(
        label='Color del Sector',
        empty_label="Selecciona un Color",
        queryset=Color.objects.filter(status=True),
        widget=forms.Select(
            attrs={
                'id': 'nombre_sector',
                'class': 'form-control select2',
                'placeholder': 'Color del Sector',
                'minlenght': '1',
                'maxlenght': '100'
            }),
        required=True
    )
    observacion = forms.CharField(
        label='Observaciones',
        widget=forms.TextInput(
            attrs={
                'id': 'nombre_sector',
                'class': 'form-control',
                'placeholder': '(Opcional)',
                'minlenght': '1',
                'maxlenght': '100'
            }),
        required=False
    )

    establecimiento = forms.ModelChoiceField(
        label="Establecimiento",
        empty_label="Selecciona una Establecimiento",
        queryset=Establecimiento.objects.filter(status=True),
        widget=forms.Select(
            attrs={
                'id': 'establecimiento_sector',
                'class': 'form-control select2',
            }),
        required=True
    )

    class Meta:
        model = Sector
        fields = ['color', 'establecimiento', 'codigo', 'observacion', ]
