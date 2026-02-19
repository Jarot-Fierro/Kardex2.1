from django import forms

from clinica.models.movimiento_ficha_monologo_controlado import MovimientoMonologoControlado
from establecimientos.models.servicio_clinico import ServicioClinico
from personas.models.profesionales import Profesional


class MovimientoSalidaForm(forms.ModelForm):
    rut = forms.CharField(label='RUT Paciente', widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_rut'}))
    nombre = forms.CharField(label='Nombre Paciente', required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'readonly': True, 'id': 'nombre_paciente'}))
    ficha = forms.CharField(label='N° Ficha', required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'readonly': True, 'id': 'numero_ficha'}))
    ficha_id_hidden = forms.CharField(widget=forms.HiddenInput(attrs={'id': 'id_ficha_hidden'}), required=False)

    servicio_clinico_destino = forms.ModelChoiceField(
        queryset=ServicioClinico.objects.none(),
        label='Servicio Clínico Destino',
        widget=forms.Select(attrs={'class': 'form-control select2', 'id': 'id_servicio_clinico_destino'})
    )
    fecha_salida = forms.DateTimeField(label='Fecha Salida', widget=forms.DateTimeInput(
        attrs={'class': 'form-control', 'type': 'datetime-local', 'id': 'id_fecha_salida'}))
    profesional = forms.ModelChoiceField(
        queryset=Profesional.objects.none(),
        label='Profesional Destino',
        widget=forms.Select(attrs={'class': 'form-control select2', 'id': 'id_profesional'})
    )
    observacion_salida = forms.CharField(label='Observación Salida', widget=forms.Textarea(
        attrs={'class': 'form-control', 'rows': 3, 'id': 'id_observacion_salida'}), required=False)

    class Meta:
        model = MovimientoMonologoControlado
        fields = ['rut', 'servicio_clinico_destino', 'profesional', 'observacion_salida', 'fecha_salida']

    def __init__(self, *args, **kwargs):
        establecimiento = kwargs.pop('establecimiento', None)
        super().__init__(*args, **kwargs)
        if establecimiento:
            self.fields['servicio_clinico_destino'].queryset = ServicioClinico.objects.filter(
                establecimiento=establecimiento)
            self.fields['profesional'].queryset = Profesional.objects.filter(
                establecimiento=establecimiento)
        else:
            self.fields['servicio_clinico_destino'].queryset = ServicioClinico.objects.all()
            self.fields['profesional'].queryset = Profesional.objects.all()


class MovimientoRecepcionForm(forms.ModelForm):
    rut = forms.CharField(label='RUT Paciente', widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_rut'}))
    nombre = forms.CharField(label='Nombre Paciente', required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'readonly': True, 'id': 'nombre_mov'}))
    ficha = forms.CharField(label='N° Ficha', required=False,
                            widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': True, 'id': 'id_ficha'}))
    fecha_entrada = forms.DateTimeField(label='Fecha Entrada', widget=forms.DateTimeInput(
        attrs={'class': 'form-control', 'type': 'datetime-local', 'id': 'id_fecha_entrada'}))

    # Campos informativos de donde viene (Servicio) y quien lo tiene (Profesional)
    servicio_clinico = forms.CharField(label='Servicio Clínico (Ubicación Actual)', required=False,
                                       widget=forms.TextInput(
                                           attrs={'class': 'form-control', 'readonly': True,
                                                  'id': 'servicio_clinico_actual'}))

    profesional = forms.CharField(label='Profesional Asignado', required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'readonly': True, 'id': 'profesional_asignado'}))

    observacion_recepcion = forms.CharField(label='Observación Recepción', widget=forms.Textarea(
        attrs={'class': 'form-control', 'rows': 3, 'id': 'observacion_recepcion_ficha'}), required=False)

    class Meta:
        model = MovimientoMonologoControlado
        fields = ['rut', 'observacion_recepcion', 'fecha_entrada']


class MovimientoTraspasoForm(forms.ModelForm):
    rut = forms.CharField(label='RUT Paciente', widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_rut'}))
    nombre = forms.CharField(label='Nombre Paciente', required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'readonly': True, 'id': 'nombre_paciente'}))
    ficha = forms.CharField(label='N° Ficha', required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'readonly': True, 'id': 'numero_ficha'}))
    ficha_id_hidden = forms.CharField(widget=forms.HiddenInput(attrs={'id': 'id_ficha_hidden'}), required=False)

    servicio_clinico_destino = forms.ModelChoiceField(
        queryset=ServicioClinico.objects.none(),
        label='Servicio Clínico Destino',
        widget=forms.Select(attrs={'class': 'form-control select2', 'id': 'id_servicio_clinico_destino'})
    )
    fecha_salida = forms.DateTimeField(label='Fecha Salida', widget=forms.DateTimeInput(
        attrs={'class': 'form-control', 'type': 'datetime-local', 'id': 'id_fecha_salida'}))

    profesional = forms.ModelChoiceField(
        queryset=Profesional.objects.none(),
        label='Profesional Destino',
        widget=forms.Select(attrs={'class': 'form-control select2', 'id': 'id_profesional'})
    )
    observacion_traspaso = forms.CharField(label='Observación Traspaso', widget=forms.Textarea(
        attrs={'class': 'form-control', 'rows': 3, 'id': 'id_observacion_traspaso'}), required=False)

    class Meta:
        model = MovimientoMonologoControlado
        fields = ['rut', 'servicio_clinico_destino', 'profesional', 'observacion_traspaso', 'fecha_salida',
                  'fecha_entrada']

    def __init__(self, *args, **kwargs):
        establecimiento = kwargs.pop('establecimiento', None)
        super().__init__(*args, **kwargs)
        if establecimiento:
            self.fields['servicio_clinico_destino'].queryset = ServicioClinico.objects.filter(
                establecimiento=establecimiento)
            self.fields['profesional'].queryset = Profesional.objects.filter(
                establecimiento=establecimiento)
        else:
            self.fields['servicio_clinico_destino'].queryset = ServicioClinico.objects.all()
            self.fields['profesional'].queryset = Profesional.objects.all()


class FiltroMovimientoForm(forms.Form):
    fecha_inicio = forms.DateTimeField(
        label='Fecha Inicio', required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
    )
    fecha_termino = forms.DateTimeField(
        label='Fecha Término', required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
    )
    servicio_clinico = forms.ModelChoiceField(
        queryset=ServicioClinico.objects.none(),
        label='Servicio Clínico', required=False,
        widget=forms.Select(attrs={'class': 'form-control select2', 'id': 'id_filter_servicio_clinico'})
    )
    profesional = forms.ModelChoiceField(
        queryset=Profesional.objects.none(),
        label='Profesional', required=False,
        widget=forms.Select(attrs={'class': 'form-control select2', 'id': 'id_filter_profesional'})
    )

    def __init__(self, *args, **kwargs):
        establecimiento = kwargs.pop('establecimiento', None)
        super().__init__(*args, **kwargs)
        if establecimiento:
            self.fields['servicio_clinico'].queryset = ServicioClinico.objects.filter(establecimiento=establecimiento)
            self.fields['profesional'].queryset = Profesional.objects.filter(establecimiento=establecimiento)
        else:
            self.fields['servicio_clinico'].queryset = ServicioClinico.objects.all()
            self.fields['profesional'].queryset = Profesional.objects.all()
