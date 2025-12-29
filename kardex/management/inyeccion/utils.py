import random
import string
from datetime import date, timedelta
from typing import Optional, Sequence

from users.models import UsuarioPersonalizado


def dv_rut(number: int) -> str:
    """Calcula dígito verificador chileno."""
    s = 1
    m = 0
    while number:
        s = (s + number % 10 * (9 - m % 6)) % 11
        number //= 10
        m += 1
    return chr(s + 47) if s else 'K'


def make_rut(unique_set: set) -> str:
    while True:
        base = random.randint(5_000_000, 28_000_000)
        dv = dv_rut(base)
        rut = f"{base}-{dv}"
        if rut not in unique_set:
            unique_set.add(rut)
            return rut


def unique_code(prefix: str, unique_set: set, length: int = 8) -> str:
    while True:
        code = prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if code not in unique_set:
            unique_set.add(code)
            return code


def unique_email(unique_set: set, domain_choices: Optional[Sequence[str]] = None) -> str:
    domain_choices = list(domain_choices) if domain_choices else [
        "example.com", "mail.com", "salud.cl", "hospital.cl"
    ]
    while True:
        local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email = f"{local}@{random.choice(domain_choices)}"
        if email not in unique_set:
            unique_set.add(email)
            return email


def random_phone() -> str:
    return "+56" + str(random.randint(900000000, 999999999))


def random_name() -> tuple[str, str, str]:
    nombres = [
        "Juan", "María", "Pedro", "Ana", "Luis", "Carla", "Diego", "Camila", "Felipe", "Sofía",
        "Javier", "Valentina", "Andrés", "Paula", "Rodrigo", "Fernanda", "Ignacio", "Daniela",
        "Sebastián", "Constanza"
    ]
    apellidos = [
        "González", "Muñoz", "Rojas", "Díaz", "Pérez", "Soto", "Contreras", "Silva", "Martínez",
        "Sepúlveda", "Morales", "Rodríguez", "López", "Fuentes", "Hernández", "Torres", "Araya",
        "Flores", "Espinoza", "Valenzuela"
    ]
    return random.choice(nombres), random.choice(apellidos), random.choice(apellidos)


def random_address(comuna_nombre: str) -> str:
    calles = ["Las Flores", "Los Olivos", "Principal", "Libertad", "O'Higgins", "Prat", "Baquedano", "Lircay"]
    return f"{random.choice(calles)} {random.randint(1, 9999)}, {comuna_nombre}"


def random_birthdate(max_years: int = 100) -> date:
    today = date.today()
    min_age_days = 0
    max_age_days = 365 * max_years
    return today - timedelta(days=random.randint(min_age_days, max_age_days))


def get_or_create_seed_user() -> UsuarioPersonalizado:
    user = UsuarioPersonalizado.objects.first()
    if user:
        return user
    # Crear un usuario mínimo para asociar fichas
    username = "seed_user"
    user = UsuarioPersonalizado.objects.create(username=username, rut=make_rut(set()))
    user.set_password("seed1234")
    user.save(update_fields=["password"])
    return user
