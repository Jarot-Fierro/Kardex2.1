import random
from typing import Dict, List

from kardex.management.inyeccion.utils import random_address, random_phone, unique_email
from kardex.models import Comuna, Establecimiento, Prevision, ServicioClinico, Profesion


def seed_comunas() -> Dict[str, Comuna]:
    nombres = [
        'Sin Información', 'Iquique', 'Antofagasta', 'Calama', 'Caldera', 'Candela',
        'Lebu', 'Curanilahue', 'Cañete', 'Contulmo', 'Arauco'
    ]
    comunas: Dict[str, Comuna] = {}
    for i, nombre in enumerate(nombres, start=1):
        obj, _ = Comuna.objects.get_or_create(
            nombre=nombre.upper(),
            defaults={
                'codigo': f"COM-{i:03d}",
                'pais': None,
            }
        )
        comunas[nombre.upper()] = obj
    return comunas


def seed_establecimientos(comunas_by_name: Dict[str, Comuna]) -> List[Establecimiento]:
    data = [
        ("Hospital San Vicente", "Arauco"),
        ("Hospital Dr. Hans Gronemann", "Contulmo"),
        ("Hospital Intercultural Kallvu Llanka", "Cañete"),
        ("Hospital Santa Isabel", "Lebu"),
        ("Hospital Provincial Dr. Rafael Avaria Valenzuela", "Curanilahue"),
    ]
    ests: List[Establecimiento] = []
    for nombre, comuna_nombre in data:
        comuna = comunas_by_name[comuna_nombre.upper()]
        obj, _ = Establecimiento.objects.get_or_create(
            nombre=nombre.upper(),
            defaults={
                'direccion': random_address(comuna.nombre.title()),
                'telefono': random_phone(),
                'comuna': comuna,
            }
        )
        ests.append(obj)
    return ests


def seed_previsiones() -> List[Prevision]:
    nombres = ['Fonasa A', 'Fonasa B', 'Fonasa C', 'Fonasa D', 'Isapre', 'Prais', 'Bloqueado']
    objs: List[Prevision] = []
    for nombre in nombres:
        obj, _ = Prevision.objects.get_or_create(nombre=nombre.upper())
        objs.append(obj)
    return objs


def seed_servicios_clinicos(establecimientos: List[Establecimiento]) -> List[ServicioClinico]:
    nombres = [
        'Cirugía Infantil', 'Cirugía Menos', 'Control Seriado', 'Dental APS', 'Dirección',
        'EMPA', 'Endodoncia', 'Obstetricia'
    ]
    objs: List[ServicioClinico] = []
    for nombre in nombres:
        obj, _ = ServicioClinico.objects.get_or_create(
            nombre=nombre.upper(),
            defaults={
                'tiempo_horas': random.choice([4, 6, 8, 12]),
                'correo_jefe': unique_email(set(), domain_choices=["servicios.clinic", "hospital.cl"]),
                'telefono': random_phone(),
                'establecimiento': random.choice(establecimientos),
            }
        )
        objs.append(obj)
    return objs


def seed_profesiones() -> List[Profesion]:
    nombres = [
        'Médico', 'Enfermero', 'Técnico', 'Kinesiólogo', 'Psicólogo', 'Odontólogo', 'Matrona',
        'Fonoaudiólogo', 'Nutricionista', 'Terapeuta Ocupacional', 'Trabajador Social', 'Químico Farmacéutico'
    ]
    objs: List[Profesion] = []
    for nombre in nombres:
        obj, _ = Profesion.objects.get_or_create(nombre=nombre.upper())
        objs.append(obj)
    return objs
