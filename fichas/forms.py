from django import forms

from clinica.models import Ficha
from personas.models.pacientes import Paciente


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = [
            'rut', 'nombre', 'apellido_paterno', 'apellido_materno', 'nombre_social',
            'pasaporte', 'nip', 'sexo', 'genero', 'estado_civil',
            'recien_nacido', 'extranjero', 'pueblo_indigena', 'fallecido', 'fecha_fallecimiento',
            'rut_madre', 'nombres_madre', 'nombres_padre', 'nombre_pareja',
            'representante_legal', 'rut_responsable_temporal', 'usar_rut_madre_como_responsable',
            'direccion', 'comuna', 'prevision', 'ocupacion', 'numero_telefono1', 'numero_telefono2', 'sin_telefono',
            'alergico_a', 'fecha_nacimiento',
        ]
        widgets = {
            'fecha_fallecimiento': forms.DateInput(attrs={'type': 'date', 'class': 'text-danger text-bold'},
                                                   format='%Y-%m-%d'),
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'rut': forms.TextInput(attrs={'class': 'id_rut'}),
            'rut_madre': forms.TextInput(attrs={'class': 'id_rut'}),
            'rut_responsable_temporal': forms.TextInput(attrs={'class': 'id_rut'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            existing_classes = field.widget.attrs.get('class', '')

            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = f'{existing_classes} form-check-input'.strip()
            else:
                field.widget.attrs['class'] = f'{existing_classes} form-control form-control-sm'.strip()


class FichaForm(forms.ModelForm):
    class Meta:
        model = Ficha
        fields = [
            'numero_ficha_sistema',
            'pasivado',
            'observacion',
            'fecha_creacion_anterior',
            'paciente',
            'sector',
        ]
        widgets = {
            'fecha_creacion_anterior': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        establecimiento = kwargs.pop('establecimiento', None)
        super().__init__(*args, **kwargs)

        if establecimiento:
            from establecimientos.models.sectores import Sector
            self.fields['sector'].queryset = Sector.objects.filter(establecimiento=establecimiento, status=True)

        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control form-control-sm'
