from django import forms
from django.core.exceptions import ValidationError

from config.validations import validate_spaces, validate_rut, format_rut
from kardex.choices import GENERO_CHOICES
from kardex.models import Paciente, Comuna, Prevision, Sector
from users.models import UsuarioPersonalizado


class PacienteFechaRangoForm(forms.Form):
    fecha_inicio = forms.DateField(
        label='Fecha inicio',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True,
    )
    fecha_fin = forms.DateField(
        label='Fecha fin',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True,
    )


class FormPacienteSinRut(forms.ModelForm):
    def clean(self):
        cleaned = super().clean()
        # Validar unicidad de identificadores excluyendo la propia instancia cuando existe (modo actualización)
        instance_pk = getattr(self.instance, 'pk', None)
        from kardex.models import Paciente as Pac
        # Campos únicos en el modelo: rut, nip, pasaporte, codigo (codigo no está en el form)
        rut = cleaned.get('rut')
        nip = cleaned.get('nip')
        pasaporte = cleaned.get('pasaporte')

        # Normalizar como lo hace el modelo.save()
        if rut:
            rut = rut.lower().strip()
            cleaned['rut'] = rut
        if nip:
            nip = nip.strip()
        if pasaporte:
            pasaporte = pasaporte.strip()

        errors = {}
        if rut:
            qs = Pac.objects.filter(rut=rut)
            if instance_pk:
                qs = qs.exclude(pk=instance_pk)
            if qs.exists():
                errors['rut'] = 'Ya existe Paciente con este Rut.'
        if nip:
            qs = Pac.objects.filter(nip=nip)
            if instance_pk:
                qs = qs.exclude(pk=instance_pk)
            if qs.exists():
                errors['nip'] = 'Ya existe Paciente con este NIE.'
        if pasaporte:
            qs = Pac.objects.filter(pasaporte=pasaporte)
            if instance_pk:
                qs = qs.exclude(pk=instance_pk)
            if qs.exists():
                errors['pasaporte'] = 'Ya existe Paciente con este Pasaporte.'

        if errors:
            from django.core.exceptions import ValidationError
            raise ValidationError(errors)
        return cleaned

    rut = forms.CharField(
        label='R.U.T.',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control id_rut',
            'id': 'id_rut'
        })
    )

    nombre = forms.CharField(
        label='Nombre',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el nombre',
            'id': 'nombre_paciente'
        }),
        required=False
    )

    apellido_paterno = forms.CharField(
        label='Apellido Paterno',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el apellido paterno',
            'id': 'apellido_paterno_paciente'
        }),
        required=True
    )

    apellido_materno = forms.CharField(
        label='Apellido Materno',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el apellido materno',
            'id': 'apellido_materno_paciente'
        }),
        required=True
    )

    rut_madre = forms.CharField(
        label='R.U.T. Madre',
        widget=forms.TextInput(attrs={
            'class': 'form-control id_rut',
            'placeholder': 'Opcional',
            'id': 'id_rut_madre'
        }),
        required=False
    )

    fecha_nacimiento = forms.DateField(
        label='Fecha de nacimiento',
        widget=forms.DateInput(
            attrs={
                'class': 'form-control fecha-input',
                'type': 'text',
                'placeholder': 'dd/mm/aaaa'
            },
            format='%d/%m/%Y'
        ),
        input_formats=['%d/%m/%Y'],
        required=True
    )

    sexo = forms.ChoiceField(
        label='Sexo',
        choices=Paciente._meta.get_field('sexo').choices,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'sexo_paciente'}),
        required=True
    )

    estado_civil = forms.ChoiceField(
        label='Estado Civil',
        choices=Paciente._meta.get_field('estado_civil').choices,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'estado_civil_paciente'}),
        required=True
    )

    nombres_padre = forms.CharField(
        label='Nombres del Padre',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Opcional',
            'id': 'nombres_padre_paciente'
        }),
        required=False
    )

    nombres_madre = forms.CharField(
        label='Nombres de la Madre',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Opcional',
            'id': 'nombres_madre_paciente'
        }),
        required=False
    )

    nombre_pareja = forms.CharField(
        label='Nombre de la Pareja',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Opcional',
            'id': 'nombre_pareja_paciente'
        }),
        required=False
    )

    direccion = forms.CharField(
        label='Dirección',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ejemplo: O’Higgins 123',
            'id': 'direccion_paciente'
        }),
        required=False
    )

    numero_telefono1 = forms.CharField(
        label='Teléfono 1',
        widget=forms.TextInput(attrs={
            'class': 'form-control telefono_personal',
            'placeholder': '+56912345678',
            'id': 'telefono_personal'
        }),
        required=False
    )

    numero_telefono2 = forms.CharField(
        label='Teléfono 2',
        widget=forms.TextInput(attrs={
            'class': 'form-control telefono_personal',
            'placeholder': 'Opcional',
            'id': 'numero_telefono2_paciente'
        }),
        required=False
    )

    pasaporte = forms.CharField(
        label='Pasaporte',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Opcional',
            'id': 'pasaporte_paciente'
        }),
        required=False
    )

    nip = forms.CharField(
        label='NIP',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Opcional',
            'id': 'nip_paciente'
        }),
        required=False
    )

    rut_responsable_temporal = forms.CharField(
        label='RUT Responsable Temporal',
        widget=forms.TextInput(attrs={
            'class': 'form-control id_rut',
            'placeholder': 'Opcional',
            'id': 'rut_responsable_temporal_paciente'
        }),
        required=False
    )

    usar_rut_madre_como_responsable = forms.BooleanField(
        label='Usar RUT de la madre como responsable',
        required=False,
        widget=forms.CheckboxInput(attrs={'id': 'usar_rut_madre_como_responsable_paciente'})
    )

    recien_nacido = forms.BooleanField(
        label='¿Es recién nacido?',
        required=False,
        widget=forms.CheckboxInput(attrs={'id': 'recien_nacido_paciente'})
    )

    extranjero = forms.BooleanField(
        label='¿Es extranjero?',
        required=False,
        widget=forms.CheckboxInput(attrs={'id': 'extranjero_paciente'})
    )

    fallecido = forms.BooleanField(
        label='¿Está fallecido?',
        required=False,
        widget=forms.CheckboxInput(attrs={'id': 'fallecido_paciente'})
    )

    fecha_fallecimiento = forms.DateField(
        label='Fecha de Fallecimiento',
        widget=forms.DateInput(
            attrs={
                'id': 'fecha_fallecimiento_paciente',
                'class': 'form-control fecha-input',
                'type': 'text',
                'placeholder': 'dd/mm/aaaa'
            },
            format='%d/%m/%Y'
        ),
        input_formats=['%d/%m/%Y'],
        required=False
    )

    ocupacion = forms.CharField(
        label='Ocupación',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ejemplo: Docente',
            'id': 'ocupacion_paciente'
        }),
        required=False
    )

    representante_legal = forms.CharField(
        label='Representante Legal',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Opcional',
            'id': 'representante_legal_paciente'
        }),
        required=False
    )

    nombre_social = forms.CharField(
        label='Nombre Social',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Opcional',
            'id': 'nombre_social_paciente'
        }),
        required=False
    )
    alergico_a = forms.CharField(
        label='Alergico a',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Opcional (Componente separado por comas)',
            'id': 'alergico_a_paciente'
        }),
        required=False
    )

    sin_telefono = forms.BooleanField(
        label='Sin Teléfono',
        required=False,
        widget=forms.CheckboxInput(attrs={'id': 'sin_telefono_paciente'})
    )

    comuna = forms.ModelChoiceField(
        label='Comuna',
        empty_label='Seleccione una Comuna',
        queryset=Comuna.objects.filter(status='ACTIVE'),
        widget=forms.Select(attrs={'class': 'form-control select2', 'id': 'comuna_paciente'}),
        required=True
    )
    sector = forms.ModelChoiceField(
        label='Sector',
        empty_label='Seleccione un Sector',
        queryset=Sector.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2', 'id': 'sector_paciente'}),
        required=False
    )

    genero = forms.ChoiceField(
        label='Estado Civil',
        choices=GENERO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'genero_paciente'}),
        required=True
    )

    prevision = forms.ModelChoiceField(
        label='Previsión',
        empty_label='Seleccione una Previsión',
        queryset=Prevision.objects.filter(status='ACTIVE'),
        widget=forms.Select(attrs={'class': 'form-control select2', 'id': 'prevision_paciente'}),
        required=True
    )

    usuario = forms.ModelChoiceField(
        label='Usuario Login',
        empty_label='Seleccione un Usuario',
        queryset=UsuarioPersonalizado.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2', 'id': 'usuario_paciente'}),
        required=False
    )

    # --- Validaciones de espacios para todos los campos de texto ---

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if not rut:
            return rut
        # Quitar espacios al inicio o final
        rut = rut.strip()

        # Validar que no contenga espacios internos
        if " " in rut:
            raise ValidationError("El RUT no debe contener espacios.")

        # Eliminar puntos y guión para validar
        rut_sin_formato = rut.replace(".", "").replace("-", "").upper()

        # Validar usando tu validador existente
        if not validate_rut(rut_sin_formato):
            raise ValidationError("El RUT ingresado no es válido.")

        # Si es válido, devolverlo formateado correctamente
        return format_rut(rut_sin_formato)

    def clean_nombre(self):
        value = self.cleaned_data.get('nombre', '')
        if value:
            validate_spaces(value)
        return value

    def clean_apellido_paterno(self):
        value = self.cleaned_data.get('apellido_paterno', '')
        if value:
            validate_spaces(value)
        return value

    def clean_apellido_materno(self):
        value = self.cleaned_data.get('apellido_materno', '')
        if value:
            validate_spaces(value)
        return value

    def clean_nombres_padre(self):
        value = self.cleaned_data.get('nombres_padre', '')
        if value:
            validate_spaces(value)
        return value

    def clean_nombres_madre(self):
        value = self.cleaned_data.get('nombres_madre', '')
        if value:
            validate_spaces(value)
        return value

    def clean_nombre_pareja(self):
        value = self.cleaned_data.get('nombre_pareja', '')
        if value:
            validate_spaces(value)
        return value

    def clean_direccion(self):
        value = self.cleaned_data.get('direccion', '')
        return value

    def clean_ocupacion(self):
        value = self.cleaned_data.get('ocupacion', '')
        if value:
            validate_spaces(value)
        return value

    def clean_representante_legal(self):
        value = self.cleaned_data.get('representante_legal', '')
        if value:
            validate_spaces(value)
        return value

    def clean_nombre_social(self):
        value = self.cleaned_data.get('nombre_social', '')
        if value:
            validate_spaces(value)
        return value

    def clean_alergico_a(self):
        value = self.cleaned_data.get('alergico_a', '')
        if value:
            validate_spaces(value)
        return value

    class Meta:
        model = Paciente
        fields = [
            'rut',
            'nip',
            'pasaporte',
            'nombre',
            'apellido_paterno',
            'apellido_materno',
            'rut_madre',
            'rut_responsable_temporal',
            'usar_rut_madre_como_responsable',
            'fecha_nacimiento',
            'sexo',
            'estado_civil',
            'nombres_padre',
            'nombres_madre',
            'nombre_pareja',
            'direccion',
            'numero_telefono1',
            'numero_telefono2',
            'recien_nacido',
            'extranjero',
            'fallecido',
            'fecha_fallecimiento',
            'ocupacion',
            'representante_legal',
            'nombre_social',
            'comuna',
            'prevision',
            'usuario',
            'genero',
            'pueblo_indigena',
            'alergico_a',
            'sin_telefono',
            'sector',
        ]


class FormPacienteActualizarRut(forms.ModelForm):
    rut = forms.CharField(
        label='R.U.T.',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control id_rut',
            'id': 'id_rut',
            'placeholder': 'Ingrese RUT (ej: 12345678-9)'
        })
    )

    class Meta:
        model = Paciente
        fields = ['rut']

    # Validación de formato de RUT reutilizando validadores existentes
    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if not rut:
            return rut
        rut = rut.strip()
        if " " in rut:
            raise ValidationError("El RUT no debe contener espacios.")
        rut_sin_formato = rut.replace(".", "").replace("-", "").upper()
        if not validate_rut(rut_sin_formato):
            raise ValidationError("El RUT ingresado no es válido.")
        return format_rut(rut_sin_formato)

    # Asegurar unicidad excluyendo la instancia actual
    def clean(self):
        cleaned = super().clean()
        rut = cleaned.get('rut')
        if not rut:
            return cleaned
        instance_pk = getattr(self.instance, 'pk', None)
        qs = Paciente.objects.filter(rut=rut)
        if instance_pk:
            qs = qs.exclude(pk=instance_pk)
        if qs.exists():
            raise ValidationError({'rut': 'Ya existe Paciente con este Rut.'})
        return cleaned
