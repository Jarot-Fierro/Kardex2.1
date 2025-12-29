import itertools
import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email
from django.utils.formats import date_format


def validate_spaces(value):
    if re.search(r"\s{2,}", value):
        raise ValidationError("Solo se permite un espacio entre palabras.")
    return value


def validate_exists(value, exists):
    if exists:
        raise ValidationError(f"Ya existe un registro con este nombre.")
    return value


def validate_date_start_end(start_date, end_date):
    if not start_date:
        raise ValidationError("La fecha de inicio es requerida.")

    if not end_date:
        raise ValidationError("La fecha de fin es requerida.")

    if end_date <= start_date:
        formatted_date = date_format(start_date, "d \d\e F \d\e Y")
        raise ValidationError(f"La fecha de fin debe ser posterior a la fecha de inicio ({formatted_date}).")

    return end_date


def validate_name(name):
    # Solo letra, números y espacios
    pattern = r'^([A-Za-zÁÉÍÓÚÑáéíóúñ0-9]+)([ -]([A-Za-zÁÉÍÓÚÑáéíóúñ0-9]+))*$'
    if not re.fullmatch(pattern, name):
        raise ValidationError("Solo se permiten letras, números, y un espacio o guión entre palabras.")

    return name


def validate_name_user(name):
    # Validar formato: solo letras, un espacio entre palabras, mínimo dos palabras
    pattern = r'^([A-Za-zÁÉÍÓÚÑáéíóúñ]+)( [A-Za-zÁÉÍÓÚÑáéíóúñ]+)+$'
    if not re.fullmatch(pattern, name.strip()):
        raise ValidationError(
            "El nombre solo puede contener letras y un espacio entre palabras. Debe tener al menos dos palabras")

    return name


def validate_description(description):
    if not description:
        return description

    if '  ' in description:
        raise ValidationError("Solo se permite un espacio entre palabras.")

    # Solo letra, números, exclamaciones, interrogación y espacios
    if not re.fullmatch(r'[A-Za-zÁÉÍÓÚÑáéíóúñ0-9¿?¡!\-.,]+(?: [A-Za-zÁÉÍÓÚÑáéíóúñ0-9¿?¡!\-.,]+)*', description):
        raise ValidationError(
            "Solo se permiten letras, números, signos (!¡¿?.,-), y un espacio entre palabras."
        )
    return description


def validate_email(email):
    email = email.strip()
    try:
        django_validate_email(email)
    except ValidationError:
        raise ValidationError("El correo electrónico no es válido.")
    return email


def validate_rut(rut: str) -> bool:
    """Valida un RUT chileno en formato con o sin puntos y guión."""
    if not rut:
        return False

    rut = rut.replace(".", "").replace("-", "").upper()

    if len(rut) < 2:
        return False

    body, dv = rut[:-1], rut[-1]

    if not body.isdigit() or len(body) < 7:
        return False

    # Cálculo del dígito verificador
    reversed_digits = map(int, reversed(body))
    factors = itertools.cycle(range(2, 8))
    total = sum(d * f for d, f in zip(reversed_digits, factors))

    remainder = total % 11
    expected = 11 - remainder

    if expected == 11:
        dv_expected = "0"
    elif expected == 10:
        dv_expected = "K"
    else:
        dv_expected = str(expected)

    return dv == dv_expected


def format_rut(rut: str) -> str:
    """Normaliza un RUT chileno al formato estándar XX.XXX.XXX-DV"""
    if not rut:
        return ""

    # Limpieza
    rut = rut.replace(".", "").replace("-", "").upper()
    body, dv = rut[:-1], rut[-1]

    # Insertar puntos de miles
    body = f"{int(body):,}".replace(",", ".")  # 21226305 -> 21.226.305

    return f"{body}-{dv}"
