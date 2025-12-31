from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from core.validations import validate_rut
from users.models import User, Role


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="RUT",
        widget=forms.TextInput(attrs={
            'id': 'id_rut',
            'class': 'form-control',
            'placeholder': 'Ej: 12.345.678-9'
        }),
        required=True
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña'
        }),
        required=True
    )

    error_messages = {
        'invalid_login': 'RUT o contraseña incorrectos',
        'inactive': 'Este usuario se encuentra inactivo',
    }

    class Meta:
        model = User


class FormUsuario(forms.ModelForm):

    def __init__(self, *args, establecimiento=None, request=None, **kwargs):
        self.establecimiento = establecimiento
        self.request = request
        super().__init__(*args, **kwargs)

    username = forms.CharField(
        label='R.U.T',
        widget=forms.TextInput(attrs={
            'id': 'id_rut',
            'class': 'form-control',
            'placeholder': 'Ej. 12.345.678-9',
        }),
        required=True
    )
    first_name = forms.CharField(
        label='Nombre',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre',
        }),
        required=True
    )
    last_name = forms.CharField(
        label='Apellido',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellido',
        }),
        required=True
    )
    email = forms.EmailField(
        label='Correo',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ejemplo@gmail.cl',
        }),
        required=False
    )
    roles = forms.ModelChoiceField(
        label='Rol',
        empty_label='Seleccione un Rol',
        queryset=Role.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
        required=True
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar contraseña'}),
        required=True
    )

    def clean_username(self):
        username = self.cleaned_data['username']

        if self.establecimiento:
            existe = User.objects.filter(username__iexact=username, establecimiento=self.establecimiento)
            if self.instance.pk:
                existe = existe.exclude(pk=self.instance.pk)

            if existe.exists():
                raise ValidationError("El usuario ya existe en este establecimiento.")

            rut = username.strip()

            # Validar que no contenga espacios
            if " " in rut:
                raise ValidationError("El RUT no debe contener espacios.")

            rut_sin_formato = rut.replace(".", "").replace("-", "").upper()

            if not validate_rut(rut_sin_formato):
                raise ValidationError("El RUT ingresado no es válido.")

        return username

    def clean_password2(self):
        password1 = self.cleaned_data['password1']
        password2 = self.cleaned_data['password2']

        # Verifica contraseñas
        if password1 and password2 and password1 != password2:
            raise ValidationError("Las contraseñas no coinciden.")

    def save(self, commit=True):
        user = super().save(commit=False)

        # hasheo aquí
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()
        return user

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'roles', 'password1', 'password2', ]
