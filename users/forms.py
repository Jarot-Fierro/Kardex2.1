from django import forms
from django.contrib.auth.forms import AuthenticationForm

from users.models import User


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
