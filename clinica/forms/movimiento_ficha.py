from django import forms
from django.forms import DateInput
from django.utils import timezone

from clinica.models import MovimientoFicha, Ficha
from core.choices import ESTADO_RESPUESTA
from establecimientos.models.establecimiento import Establecimiento
from establecimientos.models.servicio_clinico import ServicioClinico
from personas.models.profesionales import Profesional


class FormEntradaFicha(forms.ModelForm):
    rut = forms.CharField(
        label='RUT',
        required=False,
        widget=forms.TextInput(attrs={
            'id': 'id_rut',
            'class': 'form-control id_rut',
            'placeholder': 'Ingrese RUT (sin puntos, con guión)'
        })
    )

    nombre = forms.CharField(
        label='Nombre del paciente',
        required=True,
        widget=forms.TextInput(attrs={
            'id': 'nombre_mov',
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )

    # Nuevo campo de solo lectura para mostrar el Servicio Clínico de Envío (origen)
    servicio_clinico_envio = forms.CharField(
        label='Servicio Clínico de Envío',
        widget=forms.TextInput(
            attrs={
                'id': 'servicio_clinico_envio_ficha',
                'class': 'form-control',
                'readonly': 'readonly',
            }
        ),
        required=False
    )

    servicio_clinico_recepcion = forms.CharField(
        label='Servicio Clínico de Recepción',
        widget=forms.TextInput(
            attrs={
                'id': 'servicio_clinico_ficha',
                'class': 'form-control',
                'readonly': 'readonly',
            }
        ),
        required=False
    )

    observacion_recepcion = forms.CharField(
        label='Observación de Recepción',
        widget=forms.Textarea(attrs={
            'id': 'observacion_recepcion_ficha',
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Ingrese una observación de recepción (opcional)'
        }),
        required=False
    )

    ficha = forms.CharField(
        label='Ficha',
        widget=forms.TextInput(
            attrs={
                'id': 'id_ficha',
                'class': 'form-control id_ficha'
            }
        ),
        required=True
    )

    profesional_recepcion = forms.ModelChoiceField(
        label='Profesional que recibe',
        empty_label="Seleccione un Profesional",
        queryset=Profesional.objects.filter(status=True).all(),
        widget=forms.Select(
            attrs={
                'id': 'profesional_movimiento',
                'class': 'form-control select2',
            }
        ),
        required=True
    )

    def __init__(self, *args, **kwargs):
        # Permite acceder al usuario/solicitud desde el form
        self.request = kwargs.pop('request', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user is None and self.request is not None:
            self.user = getattr(self.request, 'user', None)

        # Filtrar opciones por establecimiento del usuario
        est = getattr(self.user, 'establecimiento', None)
        if est:
            self.fields['profesional_recepcion'].queryset = Profesional.objects.filter(establecimiento=est, status=True)

    def get_initial(self):
        initial = super().get_initial()
        user = getattr(self, 'user', None)
        if user and hasattr(user, 'servicio_clinico') and user.servicio_clinico:
            initial['servicio_clinico_recepcion'] = user.servicio_clinico.nombre
        return initial

    def clean_ficha(self):
        # Si ya tenemos una instancia (estamos actualizando), la ficha ya está asociada.
        if self.instance and self.instance.pk:
            return self.instance.ficha

        raw = self.cleaned_data.get('ficha')
        user = getattr(self, 'user', None)
        if user is None and getattr(self, 'request', None) is not None:
            user = getattr(self.request, 'user', None)

        # Validar usuario y establecimiento
        if not user or not hasattr(user, 'establecimiento') or user.establecimiento is None:
            raise forms.ValidationError("No se pudo determinar el establecimiento del usuario.")

        # Normalizar y validar número de ficha
        try:
            numero = int(str(raw).strip())
        except (TypeError, ValueError):
            raise forms.ValidationError("El número de ficha debe ser numérico válido.")

        # Filtrar por ficha y establecimiento del usuario
        qs = Ficha.objects.filter(numero_ficha_sistema=numero, establecimiento=user.establecimiento)

        if not qs.exists():
            raise forms.ValidationError("Ficha no encontrada en su establecimiento.")
        if qs.count() > 1:
            raise forms.ValidationError(
                "Existen múltiples fichas con ese número en su establecimiento. Contacte al administrador.")
        return qs.get()

    class Meta:
        model = MovimientoFicha
        fields = [
            'observacion_recepcion',
            'rut',
            'ficha',
            'profesional_recepcion',
            'nombre',
        ]


class FormSalidaFicha(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filtrar opciones por establecimiento del usuario
        est = getattr(self.user, 'establecimiento', None)
        if est:
            self.fields['servicio_clinico_envio'].queryset = ServicioClinico.objects.filter(establecimiento=est,
                                                                                            status=True)
            self.fields['servicio_clinico_recepcion'].queryset = ServicioClinico.objects.filter(establecimiento=est,
                                                                                                status=True)
            self.fields['profesional_envio'].queryset = Profesional.objects.filter(establecimiento=est, status=True)

        # Si el usuario tiene un servicio asignado, usarlo como inicial para envío
        if self.user and hasattr(self.user, 'servicio_clinico') and self.user.servicio_clinico:
            self.fields['servicio_clinico_envio'].initial = self.user.servicio_clinico

    rut = forms.CharField(
        label='RUT',
        required=True,
        widget=forms.TextInput(
            attrs={
                'id': 'id_rut',
                'class': 'form-control id_rut',
                'name': 'rut',
                'autocomplete': 'off',
                'inputmode': 'text',
                'placeholder': '12.345.678-9'
            }
        )
    )

    ficha = forms.CharField(
        label='Ficha',
        widget=forms.TextInput(
            attrs={
                'id': 'id_ficha',
                'class': 'form-control id_ficha'
            }
        ),
        required=True
    )

    nombre = forms.CharField(
        label='Nombre del paciente',
        required=True,
        widget=forms.TextInput(
            attrs={
                'id': 'nombre_mov',
                'class': 'form-control',
                'readonly': 'readonly'
            }
        )
    )
    servicio_clinico_envio = forms.ModelChoiceField(
        label='Servicio Clínico de Envío',
        empty_label="Selecciona un Servicio Clínico",
        queryset=ServicioClinico.objects.filter(status=True).all(),
        widget=forms.Select(
            attrs={
                'id': 'servicio_clinico_ficha',
                'class': 'form-control select2'
            }
        ),
        required=True
    )

    servicio_clinico_recepcion = forms.ModelChoiceField(
        label='Servicio Clínico de Recepción',
        empty_label="Selecciona un Servicio Clínico",
        queryset=ServicioClinico.objects.filter(status=True).all(),
        widget=forms.Select(
            attrs={
                'id': 'servicio_clinico_recepcion',
                'class': 'form-control select2'
            }
        ),
        required=True
    )

    observacion_envio = forms.CharField(
        label='Observación de Envío',
        widget=forms.Textarea(attrs={
            'id': 'observacion_envio_ficha',
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Ingrese una observación de envío (opcional)'
        }),
        required=False
    )
    profesional_envio = forms.ModelChoiceField(
        label='Profesional que envía',
        empty_label="Seleccione un Profesional",
        queryset=Profesional.objects.filter(status=True).all(),
        widget=forms.Select(
            attrs={
                'id': 'profesional_movimiento',
                'class': 'form-control select2'
            }
        ),
        required=True
    )

    def clean(self):
        cleaned_data = super().clean()
        envio = cleaned_data.get('servicio_clinico_envio')
        recepcion = cleaned_data.get('servicio_clinico_recepcion')

        if envio and recepcion and envio == recepcion:
            self.add_error('servicio_clinico_recepcion', 'El servicio de recepción no puede ser igual al de envío.')

        return cleaned_data

    ficha_id_hidden = forms.CharField(
        widget=forms.HiddenInput(attrs={'id': 'id_ficha_hidden'}),
        required=False
    )

    def clean_ficha(self):
        # El campo 'ficha' es un CharField en el formulario para mostrar el número de ficha del sistema,
        # pero el modelo MovimientoFicha espera una instancia de Ficha (ForeignKey).
        # Aquí validamos y retornamos la instancia si es posible.
        raw_ficha = self.cleaned_data.get('ficha')
        ficha_id = self.data.get('ficha_id_hidden') or self.data.get('ficha_id')

        if ficha_id:
            try:
                return Ficha.objects.get(pk=ficha_id)
            except (Ficha.DoesNotExist, ValueError):
                pass

        # Si no hay ficha_id_hidden, intentamos buscar por número de ficha del sistema
        if raw_ficha:
            user = getattr(self, 'user', None)
            if user and user.establecimiento:
                try:
                    return Ficha.objects.get(
                        numero_ficha_sistema=raw_ficha,
                        establecimiento=user.establecimiento
                    )
                except (Ficha.DoesNotExist, Ficha.MultipleObjectsReturned, ValueError):
                    pass

        return raw_ficha

    class Meta:
        model = MovimientoFicha
        fields = [
            'rut',
            'ficha',
            'ficha_id_hidden',
            'servicio_clinico_envio',
            'servicio_clinico_recepcion',
            'observacion_envio',
            'profesional_envio',
            'nombre',
        ]


class FormTraspasoFicha(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # Permite acceder al usuario/solicitud desde el form
        self.request = kwargs.pop('request', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user is None and self.request is not None:
            self.user = getattr(self.request, 'user', None)

        # Filtrar opciones por establecimiento del usuario
        est = getattr(self.user, 'establecimiento', None)
        if est:
            self.fields['servicio_clinico_traspaso'].queryset = ServicioClinico.objects.filter(establecimiento=est,
                                                                                               status=True)
            self.fields['profesional_traspaso'].queryset = Profesional.objects.filter(establecimiento=est, status=True)

        # Si el usuario tiene un servicio asignado, usarlo como inicial para traspaso
        if self.user and hasattr(self.user, 'servicio_clinico') and self.user.servicio_clinico:
            self.fields['servicio_clinico_traspaso'].initial = self.user.servicio_clinico

    # Campos auxiliares de búsqueda/visualización
    rut = forms.CharField(
        label='RUT',
        required=True,
        widget=forms.TextInput(attrs={
            'id': 'id_rut',
            'class': 'form-control id_rut',
            'autocomplete': 'off',
            'placeholder': '12.345.678-9'
        })
    )

    nombre = forms.CharField(
        label='Nombre del paciente',
        required=True,
        widget=forms.TextInput(attrs={
            'id': 'nombre_mov',
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )

    # Mostrar como texto (la API lo rellenará)
    servicio_clinico_envio = forms.CharField(
        label='Servicio Clínico de Envío',
        required=False,
        widget=forms.TextInput(attrs={
            'id': 'servicio_clinico_envio_ficha',
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )

    servicio_clinico_recepcion = forms.CharField(
        label='Servicio Clínico de Recepción',
        required=False,
        widget=forms.TextInput(attrs={
            'id': 'servicio_clinico_recepcion_ficha',
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )

    servicio_clinico_traspaso = forms.ModelChoiceField(
        label='Servicio Clínico de Traspaso',
        empty_label='Seleccione un Servicio Clínico',
        queryset=ServicioClinico.objects.filter(status=True).all(),
        required=True,
        widget=forms.Select(attrs={
            'id': 'servicio_clinico_ficha',
            'class': 'form-control select2',
        })
    )

    ficha = forms.CharField(
        label='Ficha',
        widget=forms.TextInput(
            attrs={
                'id': 'id_ficha',
                'class': 'form-control id_ficha'
            }
        ),
        required=True
    )

    # Observaciones
    observacion_traspaso = forms.CharField(
        label='Observación Traspaso',
        required=False,
        widget=forms.Textarea(attrs={
            'id': 'observacion_traspaso_ficha',
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Ingrese una observación de traspaso (opcional)'
        })
    )

    # Profesional traspaso
    profesional_traspaso = forms.ModelChoiceField(
        label='Profesional que traslada',
        empty_label="Seleccione un Profesional",
        queryset=Profesional.objects.filter(status=True).all(),
        widget=forms.Select(
            attrs={
                'id': 'profesional_movimiento',
                'class': 'form-control select2',
            }
        ),
        required=True
    )

    movimiento_id = forms.CharField(
        widget=forms.HiddenInput(attrs={'id': 'id_movimiento_hidden'}),
        required=False
    )

    def clean_ficha(self):
        # Si ya tenemos una instancia (estamos actualizando), la ficha ya está asociada.
        if self.instance and self.instance.pk:
            return self.instance.ficha

        raw = self.cleaned_data.get('ficha')
        user = getattr(self, 'user', None)
        if user is None and getattr(self, 'request', None) is not None:
            user = getattr(self.request, 'user', None)

        if not user or not hasattr(user, 'establecimiento') or user.establecimiento is None:
            raise forms.ValidationError("No se pudo determinar el establecimiento del usuario.")

        try:
            numero = int(str(raw).strip())
        except (TypeError, ValueError):
            raise forms.ValidationError("El número de ficha debe ser numérico válido.")

        qs = Ficha.objects.filter(numero_ficha_sistema=numero, establecimiento=user.establecimiento)
        if not qs.exists():
            raise forms.ValidationError("Ficha no encontrada en su establecimiento.")
        if qs.count() > 1:
            raise forms.ValidationError("Múltiples fichas encontradas. Contacte al administrador.")
        return qs.get()

    class Meta:
        model = MovimientoFicha
        fields = [
            'ficha',
            'profesional_traspaso',
            'rut',
            'nombre',
            'servicio_clinico_traspaso',
            'observacion_traspaso',
        ]


class FiltroSalidaFichaForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        est = getattr(self.user, 'establecimiento', None)
        if est:
            if 'servicio_clinico' in self.fields:
                self.fields['servicio_clinico'].queryset = ServicioClinico.objects.filter(establecimiento=est,
                                                                                          status=True)
            if 'profesional' in self.fields:
                self.fields['profesional'].queryset = Profesional.objects.filter(establecimiento=est, status=True)

    hora_inicio = forms.DateTimeField(
        label="Hora inicio",
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        }),
        required=False
    )
    hora_termino = forms.DateTimeField(
        label="Hora término",
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        }),
        required=False
    )
    servicio_clinico = forms.ModelChoiceField(
        label="Servicio Clínico",
        queryset=ServicioClinico.objects.filter(status=True).all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        required=False
    )

    profesional = forms.ModelChoiceField(
        label="Profesional asignado",
        queryset=Profesional.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        required=False
    )


class MovimientoFichaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Limitar opciones por establecimiento del usuario
        est = getattr(self.user, 'establecimiento', None) if self.user else None
        if est is not None:
            for fname in ['servicio_clinico_envio', 'servicio_clinico_recepcion', 'servicio_clinico_traspaso']:
                if fname in self.fields:
                    self.fields[fname].queryset = ServicioClinico.objects.filter(establecimiento=est, status=True)
            for fname in ['profesional_envio', 'profesional_recepcion', 'profesional_traspaso']:
                if fname in self.fields:
                    self.fields[fname].queryset = Profesional.objects.filter(establecimiento=est, status=True)

        # Ficha: por defecto vacío; si estamos editando, asegurar que la ficha actual esté disponible
        instance = kwargs.get('instance') or getattr(self, 'instance', None)
        if instance and getattr(instance, 'ficha_id', None):
            # Restringir a la ficha actual para que aparezca como seleccionada
            self.fields['ficha'].queryset = Ficha.objects.filter(pk=instance.ficha_id)
            self.fields['ficha'].initial = instance.ficha_id
        else:
            # Vacío, se cargará vía API por JS
            self.fields['ficha'].queryset = Ficha.objects.none()

        # Marcar el widget para JS (Select2 con AJAX hacia la API existente)
        if 'ficha' in self.fields:
            attrs = self.fields['ficha'].widget.attrs
            attrs['data-api-url'] = '/kardex/api/api_pacientes/'
            attrs['data-placeholder'] = 'Buscar por número de ficha'

        # Inicializar los campos de fecha si ya existe una instancia
        if instance:
            if instance.fecha_envio:
                self.fields['fecha_envio_date'].initial = instance.fecha_envio.date()
            if instance.fecha_recepcion:
                self.fields['fecha_recepcion_date'].initial = instance.fecha_recepcion.date()
            if instance.fecha_traspaso:
                self.fields['fecha_traspaso_date'].initial = instance.fecha_traspaso.date()

    # ---------------- CAMPOS DE FECHA (SOLO FECHA) ----------------
    fecha_envio_date = forms.DateField(
        label="Fecha de envío",
        widget=DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
                'id': 'id_fecha_envio_date'
            },
            format='%Y-%m-%d'
        ),
        required=False,
        help_text="Seleccione solo la fecha, la hora se asignará automáticamente"
    )

    fecha_recepcion_date = forms.DateField(
        label="Fecha de recepción",
        widget=DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
                'id': 'id_fecha_recepcion_date'
            },
            format='%Y-%m-%d'
        ),
        required=False,
        help_text="Seleccione solo la fecha, la hora se asignará automáticamente"
    )

    fecha_traspaso_date = forms.DateField(
        label="Fecha de traspaso",
        widget=DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
                'id': 'id_fecha_traspaso_date'
            },
            format='%Y-%m-%d'
        ),
        required=False,
        help_text="Seleccione solo la fecha, la hora se asignará automáticamente"
    )

    # ---------------- OBSERVACIONES ----------------
    observacion_envio = forms.CharField(
        label="Observación de envío",
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        required=False
    )

    observacion_recepcion = forms.CharField(
        label="Observación de recepción",
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        required=False
    )

    observacion_traspaso = forms.CharField(
        label="Observación de traspaso",
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        required=False
    )

    # ---------------- ESTADOS ----------------
    estado_envio = forms.ChoiceField(
        label="Estado de envío",
        choices=ESTADO_RESPUESTA,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )

    estado_recepcion = forms.ChoiceField(
        label="Estado de recepción",
        choices=ESTADO_RESPUESTA,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )

    estado_traspaso = forms.ChoiceField(
        label="Estado de traspaso",
        choices=ESTADO_RESPUESTA,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )

    # ---------------- SERVICIOS ----------------
    servicio_clinico_envio = forms.ModelChoiceField(
        label="Servicio clínico de envío",
        queryset=ServicioClinico.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        required=False
    )

    servicio_clinico_recepcion = forms.ModelChoiceField(
        label="Servicio clínico de recepción",
        queryset=ServicioClinico.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        required=False
    )

    servicio_clinico_traspaso = forms.ModelChoiceField(
        label="Servicio clínico de traspaso",
        queryset=ServicioClinico.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        required=False
    )
    # ---------------- PROFESIONALES ----------------
    profesional_envio = forms.ModelChoiceField(
        label="Profesional envío",
        queryset=Profesional.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        required=False
    )

    profesional_recepcion = forms.ModelChoiceField(
        label="Profesional recepción",
        queryset=Profesional.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        required=False
    )

    profesional_traspaso = forms.ModelChoiceField(
        label="Profesional traspaso",
        queryset=Profesional.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        required=False
    )

    # ---------------- ESTABLECIMIENTO ----------------
    establecimiento = forms.ModelChoiceField(
        label="Establecimiento",
        queryset=Establecimiento.objects.filter(status=True),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        required=False
    )

    # ---------------- FICHA ----------------
    ficha = forms.ModelChoiceField(
        label="Ficha",
        queryset=Ficha.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()

        # Combinar fecha seleccionada con hora actual
        now = timezone.now()

        # Para fecha de envío
        fecha_envio_date = cleaned_data.get('fecha_envio_date')
        if fecha_envio_date:
            # Combinar fecha seleccionada con hora actual
            cleaned_data['fecha_envio'] = timezone.make_aware(
                timezone.datetime.combine(fecha_envio_date, now.time())
            )
        elif self.instance and self.instance.fecha_envio:
            # Si ya existe una fecha en la instancia, mantenerla
            cleaned_data['fecha_envio'] = self.instance.fecha_envio

        # Para fecha de recepción
        fecha_recepcion_date = cleaned_data.get('fecha_recepcion_date')
        if fecha_recepcion_date:
            cleaned_data['fecha_recepcion'] = timezone.make_aware(
                timezone.datetime.combine(fecha_recepcion_date, now.time())
            )
        elif self.instance and self.instance.fecha_recepcion:
            cleaned_data['fecha_recepcion'] = self.instance.fecha_recepcion

        # Para fecha de traspaso
        fecha_traspaso_date = cleaned_data.get('fecha_traspaso_date')
        if fecha_traspaso_date:
            cleaned_data['fecha_traspaso'] = timezone.make_aware(
                timezone.datetime.combine(fecha_traspaso_date, now.time())
            )
        elif self.instance and self.instance.fecha_traspaso:
            cleaned_data['fecha_traspaso'] = self.instance.fecha_traspaso

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Si estamos creando un nuevo movimiento y no tiene fecha de envío
        if not instance.pk and not instance.fecha_envio:
            instance.fecha_envio = timezone.now()

        # Si estamos editando y se marcó como recibido sin fecha de recepción
        if self.cleaned_data.get('estado_recepcion') == 'RECIBIDO' and not instance.fecha_recepcion:
            instance.fecha_recepcion = timezone.now()

        # Si estamos editando y se marcó como traspasado sin fecha de traspaso
        if self.cleaned_data.get('estado_traspaso') == 'TRASPASADO' and not instance.fecha_traspaso:
            instance.fecha_traspaso = timezone.now()

        if commit:
            instance.save()

        return instance

    # ---------------- META ----------------
    class Meta:
        model = MovimientoFicha
        fields = [
            'fecha_envio', 'fecha_recepcion', 'fecha_traspaso',
            'observacion_envio', 'observacion_recepcion', 'observacion_traspaso',
            'estado_envio', 'estado_recepcion', 'estado_traspaso',
            'servicio_clinico_envio', 'servicio_clinico_recepcion', 'servicio_clinico_traspaso',
            'profesional_envio', 'profesional_recepcion', 'profesional_traspaso',
            'establecimiento',
            'ficha'
        ]
