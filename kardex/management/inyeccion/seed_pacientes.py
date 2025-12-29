import random
from datetime import date, timedelta
from typing import Dict, List

from django.core.exceptions import ValidationError

from kardex.choices import ESTADO_CIVIL
from kardex.management.inyeccion.utils import make_rut, unique_code, random_name, random_address, random_phone
from kardex.models import Comuna, Prevision, Establecimiento, Paciente, IngresoPaciente, Ficha
from users.models import UsuarioPersonalizado


def generate_pacientes_e_ingresos(
        count: int,
        comunas_by_name: Dict[str, Comuna],
        previsiones: List[Prevision],
        establecimientos: List[Establecimiento],
        seed_user: UsuarioPersonalizado,
) -> None:
    used_ruts = set(Paciente.objects.exclude(rut__isnull=True).values_list('rut', flat=True))
    used_nies = set(Paciente.objects.exclude(nie__isnull=True).values_list('nie', flat=True))

    for _ in range(count):
        nombre, apellido_paterno, apellido_materno = random_name()
        sexo = random.choice(['MASCULINO', 'FEMENINO'])
        estado_civil = random.choice([c[0] for c in ESTADO_CIVIL])
        comuna = random.choice(list(comunas_by_name.values()))
        prevision = random.choice(previsiones + [None])

        # Fecha de nacimiento entre 0 y 100 años atrás
        today = date.today()
        min_age_days = 0
        max_age_days = 365 * 100
        fecha_nacimiento = today - timedelta(days=random.randint(min_age_days, max_age_days))

        paciente = Paciente(
            rut=make_rut(used_ruts) if random.random() < 0.85 else None,
            nie=(unique_code('NIE-', used_nies, 7) if random.random() < 0.10 else None),
            nombre=nombre,
            apellido_paterno=apellido_paterno,
            apellido_materno=apellido_materno,
            fecha_nacimiento=fecha_nacimiento,
            sexo=sexo,
            estado_civil=estado_civil,
            direccion=random_address(comuna.nombre.title()),
            numero_telefono1=random_phone(),
            numero_telefono2=(random_phone() if random.random() < 0.4 else None),
            comuna=comuna,
            prevision=prevision,
            recien_nacido=(random.random() < 0.02),
            extranjero=(random.random() < 0.05),
            fallecido=False,
        )

        # Validar y guardar (esto generará el código PAC-XXXX en save si falta)
        paciente.full_clean()
        paciente.save()

        # Crear exactamente 5 ingresos con establecimientos distintos (máximo permitido)
        est_disponibles = random.sample(establecimientos, k=min(len(establecimientos), 5))
        for est in est_disponibles:
            ingreso = IngresoPaciente(
                paciente=paciente,
                establecimiento=est,
            )
            try:
                ingreso.full_clean()
                ingreso.save()
            except ValidationError:
                # Si por alguna razón no se puede crear (no debería ocurrir), omitir
                continue

            # Crear Ficha asociada al ingreso, con número asignado automáticamente
            ficha = Ficha(
                ingreso_paciente=ingreso,
                usuario=seed_user,
                observacion=None,
            )
            try:
                ficha.full_clean()
                ficha.save()
            except ValidationError:
                # Si falla la ficha, no detener el proceso del paciente
                continue
