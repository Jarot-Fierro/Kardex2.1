from django import forms

from kardex.models import Ficha, Establecimiento, Profesional, Paciente, Sector


class FormFicha(forms.ModelForm):
    numero_ficha_sistema = forms.IntegerField(
        label='Número de Ficha',
        widget=forms.NumberInput(attrs={
            'id': 'id_numero_ficha_sistema',
            'class': 'form-control',
            'placeholder': 'Ingrese el número de numero de ficha',
        }),
        required=True
    )
    observacion = forms.CharField(
        label='Observación',
        widget=forms.Textarea(attrs={
            'id': 'observacion_numero_ficha_sistema',
            'class': 'form-control',
            'placeholder': 'Ingrese una observación (opcional)',
            'rows': 3
        }),
        required=False
    )

    establecimiento = forms.ModelChoiceField(
        label='Establecimiento',
        empty_label='Seleccione un Establecimiento',
        queryset=Establecimiento.objects.filter(status='ACTIVE').all(),
        widget=forms.Select(attrs={
            'id': 'establecimiento_numero_ficha_sistema',
            'class': 'form-control select2'
        }),
        required=True
    )
    paciente = forms.ModelChoiceField(
        label='Paciente',
        empty_label='Seleccione un Paciente',
        queryset=Paciente.objects.none(),
        widget=forms.Select(attrs={
            'id': 'paciente-select',
            'class': 'form-control'
        }),
        required=True
    )

    sector = forms.ModelChoiceField(
        label='Sector',
        empty_label='Seleccione un Sector',
        queryset=Sector.objects.all(),
        widget=forms.Select(attrs={
            'id': 'sector_ficha_sistema',
            'class': 'form-control select2'
        }),
        required=False
    )

    class Meta:
        model = Ficha
        fields = [
            'numero_ficha_sistema',
            'paciente',
            'establecimiento',
            'sector',
            'observacion',
        ]


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
