import re

from django.db.models import Q


def get_rut_q_filter(search_value, field_name='rut'):
    """
    Filtra por RUT ignorando puntos y guión.
    """
    if not search_value:
        return Q()

    # Limpiar el valor de búsqueda (quitar puntos y guiones)
    clean_value = re.sub(r'[^0-9kK]', '', search_value).upper()

    # Búsqueda flexible en el campo RUT
    q = Q(**{f"{field_name}__icontains": search_value})
    if clean_value:
        q |= Q(**{f"{field_name}__icontains": clean_value})

    return q


def get_name_q_filter(search_value, prefix=''):
    """
    Implementa la lógica de búsqueda inteligente (fuzzy tokens).
    - Divide por palabras (tokens).
    - Cada palabra debe estar presente en nombre, apellido_paterno o apellido_materno (OR).
    - Todas las palabras deben coincidir (AND).
    """
    if not search_value:
        return Q()

    # Limpiar y tokenizar
    tokens = search_value.strip().split()
    if not tokens:
        return Q()

    # Prefijo para los campos (ej: 'paciente__')
    f_nombre = f"{prefix}nombre__icontains"
    f_paterno = f"{prefix}apellido_paterno__icontains"
    f_materno = f"{prefix}apellido_materno__icontains"

    # Construir el filtro AND de tokens
    final_q = Q()
    for token in tokens:
        # Cada token puede estar en cualquiera de los 3 campos (OR)
        token_q = Q(**{f_nombre: token}) | Q(**{f_paterno: token}) | Q(**{f_materno: token})
        if final_q:
            final_q &= token_q
        else:
            final_q = token_q

    return final_q


def build_paciente_search_q(search_value, prefix=''):
    """
    Combina búsqueda por RUT y por Nombre.
    """
    if not search_value:
        return Q()

    q_name = get_name_q_filter(search_value, prefix=prefix)
    q_rut = get_rut_q_filter(search_value, field_name=f'{prefix}rut')

    # Combinamos con OR: o coincide el nombre (con todos sus tokens) o coincide el RUT
    return q_name | q_rut
