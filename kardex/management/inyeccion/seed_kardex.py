from django.core.management.base import BaseCommand
from django.db import transaction

from kardex.management.inyeccion.utils import get_or_create_seed_user
from .seed_mantenedores import (
    seed_comunas,
    seed_establecimientos,
    seed_previsiones,
    seed_servicios_clinicos,
    seed_profesiones,
)
from .seed_pacientes import generate_pacientes_e_ingresos
from .seed_profesionales import generate_profesionales


class Command(BaseCommand):
    help = (
        "Seed fixed maintainers and generate bulk data: profesionales, pacientes, ingresos y fichas.\n"
        "Usage: python manage.py seed_kardex --profesionales 6000 --pacientes 6000 --dry-run"
    )

    def add_arguments(self, parser):
        parser.add_argument('--profesionales', type=int, default=300)
        parser.add_argument('--pacientes', type=int, default=300)
        parser.add_argument('--dry-run', action='store_true', default=False)

    def handle(self, *args, **options):
        prof_count = options['profesionales']
        pac_count = options['pacientes']
        dry_run = options['dry_run']

        with transaction.atomic():
            self.stdout.write(self.style.MIGRATE_HEADING("Seeding datos fijos (mantenedores)..."))
            comunas_by_name = seed_comunas()
            establecimientos = seed_establecimientos(comunas_by_name)
            previsiones = seed_previsiones()
            seed_servicios_clinicos(establecimientos)
            profesiones = seed_profesiones()
            seed_user = get_or_create_seed_user()

            self.stdout.write(self.style.MIGRATE_HEADING("Generando profesionales..."))
            generate_profesionales(prof_count, profesiones, establecimientos)

            self.stdout.write(self.style.MIGRATE_HEADING("Generando pacientes, ingresos y fichas..."))
            generate_pacientes_e_ingresos(pac_count, comunas_by_name, previsiones, establecimientos, seed_user)

            if dry_run:
                self.stdout.write(self.style.WARNING("Dry-run activado: se revertirán los cambios."))
                raise transaction.TransactionManagementError("Dry-run: rollback intencional")

        self.stdout.write(self.style.SUCCESS("Seeding completado correctamente."))
