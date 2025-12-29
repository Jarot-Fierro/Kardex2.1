def permisos_to_template(request):
    return {
        "user_permissions": getattr(request, 'user_roles', {})
    }
