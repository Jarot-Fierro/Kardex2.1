from django import forms

from clinica.models import Ficha, MovimientoFicha
from core.validations import validate_rut, format_rut
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
            'fecha_fallecimiento': forms.DateInput(attrs={'type': 'date', 'class': 'text-danger text-bold', 'style': 'background-color:#FFF9F2; color:#4b0082; border:1px solid #FFB95C;'},
                                                   format='%Y-%m-%d'),
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class':'text-bold', 'style': 'background-color:#F8F2FF; color:#4b0082; border:1px solid #6f42c1;'}, format='%Y-%m-%d'),
            'rut': forms.TextInput(attrs={'class': 'id_rut text-bold text-primary'}),
            'rut_madre': forms.TextInput(attrs={'class': 'id_rut'}),
            'rut_responsable_temporal': forms.TextInput(attrs={'class': 'id_rut'}),
            'numero_telefono1': forms.TextInput(attrs={'class': 'telefono_personal'}),
            'numero_telefono2': forms.TextInput(attrs={'class': 'telefono_personal'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_css_class = 'text-danger'

        for field_name, field in self.fields.items():
            existing_classes = field.widget.attrs.get('class', '')

            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = f'{existing_classes} form-check-input'.strip()
            else:
                field.widget.attrs['class'] = f'{existing_classes} form-control form-control-sm'.strip()

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if not rut:
            return rut

        # Normalizamos el RUT igual que en el modelo para comparar
        rut = rut.strip().upper()

        if validate_rut(rut):
            rut = format_rut(rut)

        # Buscamos si ya existe un paciente con este RUT
        qs = Paciente.objects.filter(rut=rut)

        # Si estamos editando (instance.pk existe), excluimos la instancia actual
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(f"El RUT {rut} ya se encuentra registrado para otro paciente.")

        return rut

    def clean(self):
        cleaned_data = super().clean()
        fallecido = cleaned_data.get('fallecido')
        fecha_fallecimiento = cleaned_data.get('fecha_fallecimiento')
        extranjero = cleaned_data.get('extranjero')
        recien_nacido = cleaned_data.get('recien_nacido')
        nip = cleaned_data.get('nip')
        rut = cleaned_data.get('rut')

        if fallecido and not fecha_fallecimiento:
            self.add_error('fecha_fallecimiento',
                           "Si el paciente ha fallecido, debe indicar la fecha de fallecimiento.")

        if extranjero and not nip and not rut:
            self.add_error('nip', "Si el paciente es extranjero, debe indicar el NIP o un RUT ficticio.")

        if not rut and not recien_nacido and not extranjero:
            self.add_error('rut', "El RUT es obligatorio para pacientes nacionales que no son recién nacidos.")

        return cleaned_data


class FichaForm(forms.ModelForm):
    class Meta:
        model = Ficha
        fields = [
            'paciente',
            'numero_ficha_sistema',
            'pasivado',
            'observacion',
            'fecha_creacion_anterior',
            'paciente',
            'sector',
        ]
        widgets = {
            'fecha_creacion_anterior': forms.DateInput(attrs={'type': 'date', 'class':'text-bold', 'style': 'background-color:#E3FFED; color:#00571C; border:1px solid #1FC24C;'}, format='%Y-%m-%d'),
            'numero_ficha_sistema': forms.NumberInput(attrs={'class': 'text-bold text-danger', 'style': 'background-color:#FFF9F2; border:1px solid #FFB95C;'}),
            'observacion': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.establecimiento = kwargs.pop('establecimiento', None)
        super().__init__(*args, **kwargs)
        self.error_css_class = 'text-danger'

        # Configurar Select2 dinámico para paciente
        self.fields['paciente'].widget.attrs.update({
            'class': 'form-control form-control-sm select2',
            'data-ajax--url': '/fichas/paciente-autocomplete/',
            'data-placeholder': 'Buscar paciente por RUT o Nombre...',
            'data-minimum-input-length': '2',
        })

        # Si hay una instancia, necesitamos cargar el paciente actual en el queryset para que aparezca
        if self.instance.pk and self.instance.paciente:
            self.fields['paciente'].queryset = Paciente.objects.filter(pk=self.instance.paciente_id)
        elif self.data and self.data.get(self.add_prefix('paciente')):
            # Si estamos en un POST con un paciente seleccionado, lo agregamos al queryset para que pase la validación
            paciente_id = self.data.get(self.add_prefix('paciente'))
            self.fields['paciente'].queryset = Paciente.objects.filter(pk=paciente_id)
        else:
            self.fields['paciente'].queryset = Paciente.objects.none()

        if self.establecimiento:
            from establecimientos.models.sectores import Sector
            self.fields['sector'].queryset = Sector.objects.filter(establecimiento=self.establecimiento, status=True)

        for field_name, field in self.fields.items():
            existing_classes = field.widget.attrs.get('class', '')
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = f'{existing_classes} form-check-input'.strip()
            else:
                field.widget.attrs['class'] = f'{existing_classes} form-control form-control-sm'.strip()

    def clean_paciente(self):
        paciente = self.cleaned_data.get('paciente')
        if not paciente:
            return paciente

        # Buscamos si el paciente ya tiene una ficha asignada
        qs = Ficha.objects.filter(paciente=paciente)

        # Si estamos editando la ficha, excluimos la ficha actual de la búsqueda
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            ficha_existente = qs.first()
            raise forms.ValidationError(
                f"El paciente {paciente.nombre_completo} ya tiene asignada la ficha "
                f"#{ficha_existente.numero_ficha_sistema or '----'} en el sistema."
            )

        return paciente

    def clean_numero_ficha_sistema(self):
        numero = self.cleaned_data.get('numero_ficha_sistema')
        if not numero:
            return numero

        # El usuario dice: "no podemos asignar una ficha que sea de otro"
        # Esto puede referirse a que el número de ficha no se repita.
        # El modelo Ficha ya tiene un UniqueConstraint para (establecimiento, numero_ficha_sistema).

        # Intentamos obtener el establecimiento desde el atributo self.establecimiento o la instancia
        establecimiento = getattr(self, 'establecimiento', None)

        # Si no está en el self, intentamos de la instancia
        if not establecimiento and self.instance.pk:
            establecimiento = self.instance.establecimiento

        if establecimiento:
            from clinica.models.ficha import Ficha
            qs = Ficha.objects.filter(establecimiento=establecimiento, numero_ficha_sistema=numero)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    f"El número de ficha {numero} ya está en uso en este establecimiento."
                )

        return numero


class FusionarPacientesForm(forms.Form):
    paciente_ficticio = forms.ModelChoiceField(
        queryset=Paciente.objects.all(),
        widget=forms.HiddenInput()
    )
    paciente_real = forms.ModelChoiceField(
        queryset=Paciente.objects.all(),
        widget=forms.HiddenInput()
    )

    # Identificadores de lo que se va a eliminar
    ficha_id_eliminar = forms.IntegerField(widget=forms.HiddenInput())
    paciente_id_eliminar = forms.IntegerField(widget=forms.HiddenInput())

    # Opción para borrar físicamente al paciente
    borrar_paciente = forms.BooleanField(
        required=False,
        initial=False,
        label="¿Desea borrar físicamente el registro del paciente ficticio?"
    )

    FICHA_CHOICES = [
        ('ficticia', 'Conservar Ficha del Paciente Ficticio'),
        ('real', 'Conservar Ficha del Paciente Real'),
    ]
    ficha_a_conservar = forms.ChoiceField(
        choices=FICHA_CHOICES,
        widget=forms.RadioSelect,
        label="Seleccione la ficha que desea conservar"
    )

    movimientos_ficticio = forms.ModelMultipleChoiceField(
        queryset=MovimientoFicha.objects.none(),
        widget=forms.MultipleHiddenInput(),
        required=False
    )
    movimientos_real = forms.ModelMultipleChoiceField(
        queryset=MovimientoFicha.objects.none(),
        widget=forms.MultipleHiddenInput(),
        required=False
    )

    confirmacion = forms.BooleanField(
        required=True,
        label="Entiendo y confirmo la fusión"
    )
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Motivo de la corrección"
    )

    def __init__(self, *args, **kwargs):
        ficticio = kwargs.pop('paciente_ficticio', None)
        real = kwargs.pop('paciente_real', None)
        super().__init__(*args, **kwargs)

        if ficticio and real:
            self.fields['paciente_ficticio'].initial = ficticio
            self.fields['paciente_real'].initial = real

            # Cargar movimientos de ambos para los checkboxes
            ficha_ficticia_qs = Ficha.objects.filter(paciente=ficticio)
            ficha_real_qs = Ficha.objects.filter(paciente=real)

            ficha_ficticia = ficha_ficticia_qs.first()
            ficha_real = ficha_real_qs.first()

            choices = []
            if ficha_ficticia:
                self.fields['movimientos_ficticio'].queryset = MovimientoFicha.objects.filter(ficha=ficha_ficticia)
                choices.append(('ficticia', f'Conservar Ficha Ficticia (#{ficha_ficticia.numero_ficha_sistema})'))
            else:
                choices.append(('ficticia', 'Paciente Ficticio (Sin Ficha)'))

            if ficha_real:
                self.fields['movimientos_real'].queryset = MovimientoFicha.objects.filter(ficha=ficha_real)
                choices.append(('real', f'Conservar Ficha Real (#{ficha_real.numero_ficha_sistema})'))
            else:
                choices.append(('real', 'Paciente Real (Sin Ficha)'))

            self.fields['ficha_a_conservar'].choices = choices

        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect, forms.HiddenInput)):
                field.widget.attrs.update({'class': 'form-control form-control-sm'})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
