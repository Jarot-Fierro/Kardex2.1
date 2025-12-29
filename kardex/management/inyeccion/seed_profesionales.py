import random
from typing import List

from kardex.management.inyeccion.utils import random_name, make_rut, unique_email, random_phone
from kardex.models import Profesion, Establecimiento
from kardex.models import Profesional


def generate_profesionales(count: int, profesiones: List[Profesion], establecimientos: List[Establecimiento]) -> None:
    used_ruts = set(
        Profesional.objects.values_list('rut', flat=True)
    )
    used_emails = set(
        Profesional.objects.values_list('correo', flat=True)
    )

    for _ in range(count):
        nombres, ap_pat, ap_mat = random_name()
        rut = make_rut(used_ruts)
        email = unique_email(used_emails)
        telefono = random_phone()
        profesion = random.choice(profesiones)
        establecimiento = random.choice(establecimientos)

        obj = Profesional(
            rut=rut,
            nombres=f"{nombres} {ap_pat} {ap_mat}",
            correo=email,
            telefono=telefono,
            profesion=profesion,
            establecimiento=establecimiento,
        )
        obj.full_clean()
        obj.save()
