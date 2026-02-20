import re

from django.db.models import Q

from core.validations import format_rut


def get_rut_q_filter(search_value, rut_field='rut'):
    """
    Genera un filtro Q para búsqueda por RUT, intentando normalizar la entrada.
    """
    # Limpiar la búsqueda de puntos y guiones
    clean_value = re.sub(r'[^0-9kK]', '', search_value).upper()

    q = Q(**{f'{rut_field}__icontains': search_value})

    if clean_value:
        # Si tiene al menos un dígito, intentamos buscar por la versión limpia
        q |= Q(**{f'{rut_field}__icontains': clean_value})

        # Si parece un RUT completo (al menos 7 caracteres), intentamos formatearlo
        if len(clean_value) >= 7:
            try:
                formatted = format_rut(clean_value)
                if formatted != search_value:
                    q |= Q(**{f'{rut_field}__icontains': formatted})
            except Exception:
                pass

    return q


def get_name_q_filter(search_value, prefix='rut_paciente__'):
    """
    Genera un filtro Q para búsqueda por nombre, apellido paterno o materno.
    """
    parts = search_value.split()
    q = Q()
    for part in parts:
        q_part = (
                Q(**{f'{prefix}nombre__icontains': part}) |
                Q(**{f'{prefix}apellido_paterno__icontains': part}) |
                Q(**{f'{prefix}apellido_materno__icontains': part})
        )
        if q:
            q &= q_part
        else:
            q = q_part
    return q
