from django import forms


class RangoFechaPacienteForm(forms.Form):
    fecha_inicio = forms.DateField(
        label="Desde",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        required=True
    )
    fecha_fin = forms.DateField(
        label="Hasta",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        required=True
    )
