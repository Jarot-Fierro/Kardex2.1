from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

# campo del modelo Role -> app.model
ROLE_FIELD_TO_MODEL = {
    'establecimientos': 'establecimientos.establecimiento',
    'paciente': 'personas.paciente',
    'fichas': 'ficha.ficha',
    'movimiento_ficha': 'ficha.movimientoficha',
    'comunas': 'personas.comuna',
    'pais': 'personas.pais',
    'prevision': 'personas.prevision',
    'profesion': 'personas.profesion',
    'profesionales': 'personas.profesional',
    'genero': 'personas.genero',
    'sectores': 'establecimientos.sector',
    'servicio_clinico': 'establecimientos.servicioclinico',
    'reportes': None,  # si después quieres permisos custom
    'soporte': None,
}

# nivel de permiso -> acciones Django
PERMISSION_LEVELS = {
    0: [],
    1: ['view'],
    2: ['view', 'add', 'change'],
    3: ['view', 'add', 'change', 'delete'],  # opcional
}


def get_permissions_for_role(role):
    """
    Retorna lista de objetos Permission según el Role
    """
    permissions = []

    for field, model_path in ROLE_FIELD_TO_MODEL.items():
        if not model_path:
            continue

        level = getattr(role, field, 0)
        if level == 0:
            continue

        app_label, model = model_path.split('.')
        actions = PERMISSION_LEVELS.get(level, [])

        try:
            content_type = ContentType.objects.get(
                app_label=app_label,
                model=model
            )
        except ContentType.DoesNotExist:
            continue

        perms = Permission.objects.filter(
            content_type=content_type,
            codename__in=[f'{a}_{model}' for a in actions]
        )

        permissions.extend(perms)

    return permissions


def sync_user_permissions(user):
    """
    Limpia y vuelve a asignar permisos según los roles del usuario
    """
    user.user_permissions.clear()

    user_roles = user.userrole_set.select_related('role_id')

    for ur in user_roles:
        role = ur.role_id
        perms = get_permissions_for_role(role)
        user.user_permissions.add(*perms)
