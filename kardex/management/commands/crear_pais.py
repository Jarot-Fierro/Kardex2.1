from django.core.management.base import BaseCommand

from kardex.models import Pais


class Command(BaseCommand):
    help = 'Crea el país CHILE'

    def handle(self, *args, **kwargs):
        obj, created = Pais.objects.update_or_create(
            cod_pais='CL',
            defaults={'nombre': 'CHILE'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ País creado: {obj}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'⚙️ País actualizado: {obj}'))
