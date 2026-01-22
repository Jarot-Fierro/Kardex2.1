from django import forms

from clinica.models import Ficha
from establecimientos.models.sectores import Sector
from personas.models.pacientes import Paciente


class FichaForm(forms.ModelForm):
    numero_ficha_sistema = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm',
            'id': 'id_ficha',
            'placeholder': 'Número de ficha sistema'
        })
    )

    pasivado = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_pasivado'
        })
    )

    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-sm',
            'rows': 3,
            'placeholder': 'Observaciones de la ficha'
        })
    )

    fecha_creacion_anterior = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control form-control-sm',
        })
    )

    sector = forms.ModelChoiceField(
        queryset=Sector.objects.filter(status=True),
        required=False,
        empty_label='Selecciona un Sector',
        widget=forms.Select(attrs={
            'class': 'form-control form-control-sm select2',
        })
    )

    paciente = forms.ModelChoiceField(
        queryset=Paciente.objects.none(),
        required=False,
        empty_label='Selecciona un Paciente',
        widget=forms.Select(attrs={
            'class': 'form-control form-control-sm select2',
            'id': 'id_paciente_select'
        })
    )

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si hay una instancia con paciente, permitimos que ese paciente esté en el queryset
        if self.instance and self.instance.paciente_id:
            self.fields['paciente'].queryset = Paciente.objects.filter(pk=self.instance.paciente_id)


class FormFichaTarjeta(forms.ModelForm):
    """
    Formulario para asignar/editar N° de Ficha (sistema) y N° de Ficha de Tarjeta.
    Muestra además: ID de la ficha, RUT del paciente y Nombre completo como sólo lectura.
    Siempre trabaja en modo actualización (UpdateView).
    """
    # Campos de solo visualización (no mapean al modelo)
    ficha_id_display = forms.CharField(
        label='ID Ficha',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    rut_display = forms.CharField(
        label='RUT Paciente',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    nombre_display = forms.CharField(
        label='Nombre Completo',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )

    # Campos editables del modelo
    numero_ficha_sistema = forms.IntegerField(
        label='Número de Ficha (Sistema)',
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'})
    )
    numero_ficha_tarjeta = forms.IntegerField(
        label='Número de Ficha de Tarjeta',
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'})
    )

    class Meta:
        model = Ficha
        fields = ['numero_ficha_sistema', 'numero_ficha_tarjeta']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prefill de campos de sólo lectura
        instance = getattr(self, 'instance', None)
        if instance is not None:
            self.fields['ficha_id_display'].initial = instance.pk
            pac = getattr(instance, 'paciente', None)
            rut = getattr(pac, 'rut', '') if pac else ''
            nombre = ''
            if pac:
                nombre = f"{pac.nombre or ''} {pac.apellido_paterno or ''} {pac.apellido_materno or ''}".strip()
            self.fields['rut_display'].initial = rut
            self.fields['nombre_display'].initial = nombre
        # Si ya tiene número de ficha, mantenerlo en el input
        # (Django ya setea initial para campos del modelo con instance)
