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


from django.core.cache import cache
from django.db import transaction


def sync_user_permissions(user):
    """
    Limpia y vuelve a asignar permisos según los roles del usuario.
    Se utiliza caché para evitar deadlocks y repeticiones innecesarias.
    """
    if not user.is_authenticated:
        return

    cache_key = f"user_perms_synced_{user.pk}"
    if cache.get(cache_key):
        return

    try:
        with transaction.atomic():
            # Obtener permisos ANTES de limpiar, por si falla algo
            user_roles = user.userrole_set.select_related('role_id').all()
            all_perms = []
            for ur in user_roles:
                all_perms.extend(get_permissions_for_role(ur.role_id))

            # Solo limpiar y añadir si los permisos han cambiado o no están sincronizados
            # Pero para simplificar y asegurar, usamos el clear/add dentro de la transacción
            # La clave es minimizar el tiempo de bloqueo.
            user.user_permissions.clear()
            if all_perms:
                # Usar set para evitar duplicados si varios roles tienen el mismo permiso
                user.user_permissions.add(*set(all_perms))
    except Exception:
        # Si hay un error (como un deadlock), simplemente no marcamos la caché
        # y dejamos que la siguiente petición intente de nuevo.
        # No bloqueamos la petición del usuario por esto.
        return

    # Marcar como sincronizado por 5 minutos
    cache.set(cache_key, True, 300)
