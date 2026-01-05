from django import forms

from users.models import Role


class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = [
            'role_name',
            'usuarios',
            'comunas',
            'establecimientos',
            'fichas',
            'genero',
            'movimiento_ficha',
            'paciente',
            'pais',
            'prevision',
            'colores_sector',
            'profesion',
            'profesionales',
            'sectores',
            'servicio_clinico',
            'reportes',
            'soporte',
            'establecimiento',
        ]
        widgets = {
            'role_name': forms.TextInput(attrs={'class': 'form-control'}),
            'usuarios': forms.Select(attrs={'class': 'form-control'}),
            'comunas': forms.Select(attrs={'class': 'form-control'}),
            'establecimientos': forms.Select(attrs={'class': 'form-control'}),
            'fichas': forms.Select(attrs={'class': 'form-control'}),
            'genero': forms.Select(attrs={'class': 'form-control'}),
            'movimiento_ficha': forms.Select(attrs={'class': 'form-control'}),
            'paciente': forms.Select(attrs={'class': 'form-control'}),
            'pais': forms.Select(attrs={'class': 'form-control'}),
            'prevision': forms.Select(attrs={'class': 'form-control'}),
            'colores_sector': forms.Select(attrs={'class': 'form-control'}),
            'profesion': forms.Select(attrs={'class': 'form-control'}),
            'profesionales': forms.Select(attrs={'class': 'form-control'}),
            'sectores': forms.Select(attrs={'class': 'form-control'}),
            'servicio_clinico': forms.Select(attrs={'class': 'form-control'}),
            'reportes': forms.Select(attrs={'class': 'form-control'}),
            'soporte': forms.Select(attrs={'class': 'form-control'}),
            'establecimiento': forms.Select(attrs={'class': 'form-control'}),
        }
