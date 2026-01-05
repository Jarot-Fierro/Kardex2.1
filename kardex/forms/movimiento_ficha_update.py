# usuarios.py
from django import forms

from kardex.models import MovimientoFicha, ServicioClinico, Profesional


class FormSalidaFicha(forms.ModelForm):
    """
    Formulario para registro de salida de fichas con carga dinámica de datos del paciente.
    """

    busqueda = forms.CharField(
        label='Buscar por RUT o Número de Ficha',
        widget=forms.TextInput(attrs={
            'id': 'id_busqueda',
            'class': 'form-control id_rut',
            'autocomplete': 'off',
            'placeholder': 'Ingrese RUT',
            'autofocus': True,
        }),
        required=True
    )

    paciente_id = forms.CharField(
        widget=forms.HiddenInput(attrs={'id': 'id_paciente_id'}),
        required=False
    )

    rut = forms.CharField(
        widget=forms.HiddenInput(attrs={'id': 'id_rut'}),
        required=False
    )

    ficha_id = forms.CharField(
        widget=forms.HiddenInput(attrs={'id': 'id_ficha_id'}),
        required=False
    )

    numero_ficha = forms.CharField(
        label='Número de Ficha',
        widget=forms.TextInput(attrs={
            'id': 'id_numero_ficha',
            'class': 'form-control',
            'readonly': True
        }),
        required=False
    )

    nombre_completo = forms.CharField(
        label='Nombre del Paciente',
        widget=forms.TextInput(attrs={
            'id': 'id_nombre_completo',
            'class': 'form-control',
            'readonly': True
        }),
        required=False
    )

    # -------------------------------------------------
    # Campos filtrables por establecimiento
    # -------------------------------------------------

    servicio_clinico_envio = forms.ModelChoiceField(
        label='Servicio Clínico de Envío',
        queryset=ServicioClinico.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'id': 'id_servicio_clinico_envio'
        }),
        required=True
    )

    servicio_clinico_recepcion = forms.ModelChoiceField(
        label='Servicio Clínico de Recepción',
        queryset=ServicioClinico.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'id': 'id_servicio_clinico_recepcion'
        }),
        required=True
    )

    profesional_envio = forms.ModelChoiceField(
        label='Profesional Responsable',
        queryset=Profesional.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'id': 'id_profesional_envio'
        }),
        required=True
    )

    observacion_envio = forms.CharField(
        label='Observación (Opcional)',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'id': 'id_observacion_envio'
        }),
        required=False
    )

    # -------------------------------------------------
    # Constructor: filtrado por usuario
    # -------------------------------------------------

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if not self.user:
            return

        establecimiento = self.user.establecimiento

        # Filtrar todos los selects por establecimiento
        self.fields['servicio_clinico_envio'].queryset = ServicioClinico.objects.filter(
            status='ACTIVE',
            establecimiento=establecimiento
        )

        self.fields['servicio_clinico_recepcion'].queryset = ServicioClinico.objects.filter(
            status='ACTIVE',
            establecimiento=establecimiento
        )

        self.fields['profesional_envio'].queryset = Profesional.objects.filter(
            status='ACTIVE',
            establecimiento=establecimiento
        )

    # -------------------------------------------------
    # Validaciones
    # -------------------------------------------------

    def clean(self):
        cleaned_data = super().clean()

        # Validar que los datos del paciente fueron cargados
        paciente_id = cleaned_data.get('paciente_id')
        ficha_id = cleaned_data.get('ficha_id')

        if not paciente_id or not ficha_id:
            raise forms.ValidationError(
                "Debe buscar y seleccionar un paciente antes de registrar la salida."
            )

        # Validar que los servicios no sean iguales
        servicio_envio = cleaned_data.get('servicio_clinico_envio')
        servicio_recepcion = cleaned_data.get('servicio_clinico_recepcion')

        if servicio_envio and servicio_recepcion and servicio_envio.id == servicio_recepcion.id:
            raise forms.ValidationError(
                "El servicio clínico de recepción no puede ser igual al servicio de envío."
            )

        return cleaned_data

    # -------------------------------------------------
    # Guardado
    # -------------------------------------------------

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Asignar usuario y establecimiento
        if self.user:
            instance.usuario_envio = self.user
            instance.establecimiento = self.user.establecimiento

        # Asignar ficha desde el ID
        ficha_id = self.cleaned_data.get('ficha_id')
        if ficha_id:
            from kardex.models import Ficha
            try:
                instance.ficha = Ficha.objects.get(id=ficha_id)
            except Ficha.DoesNotExist:
                pass

        if commit:
            instance.save()

        return instance

    class Meta:
        model = MovimientoFicha
        fields = [
            'busqueda',
            'paciente_id',
            'rut',
            'ficha_id',
            'numero_ficha',
            'nombre_completo',
            'servicio_clinico_envio',
            'servicio_clinico_recepcion',
            'profesional_envio',
            'observacion_envio',
        ]
