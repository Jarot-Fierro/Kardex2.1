from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from users.models import UserRole


@login_required
def dashboard_view(request):
    user_roles = UserRole.objects.filter(user_id=request.user)

    permissions = {
        'comunas': 0,
        'establecimientos': 0,
        'fichas': 0,
        'genero': 0,
        'movimiento_ficha': 0,
        'paciente': 0,
        'pais': 0,
        'prevision': 0,
        'colores_sector': 0,
        'profesion': 0,
        'profesionales': 0,
        'sectores': 0,
        'servicio_clinico': 0,
        'soporte': 0,
    }

    for user_role in user_roles:
        role = user_role.role_id
        for module in permissions.keys():
            current_permission = getattr(role, module)
            if current_permission > permissions[module]:
                permissions[module] = current_permission

    return render(request, 'core/dashboard.html', {'permissions': permissions})
