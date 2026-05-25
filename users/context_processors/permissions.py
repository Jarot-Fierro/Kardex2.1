from django.conf import settings

def permisos_to_template(request):
    force_script_name = settings.FORCE_SCRIPT_NAME_TO_HTML
    if force_script_name:
        if not force_script_name.startswith('/'):
            force_script_name = '/' + force_script_name
        if not force_script_name.endswith('/'):
            force_script_name = force_script_name + '/'
    else:
        force_script_name = '/'

    return {
        "user_permissions": getattr(request, 'user_roles', {}),
        "BASE_URL": force_script_name
    }
