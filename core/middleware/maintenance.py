from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Verificar si el modo mantenimiento está activado en settings
        maintenance_mode = getattr(settings, 'MAINTENANCE_MODE', False)

        if maintenance_mode:
            path = request.path
            maintenance_url = reverse('maintenance')

            # Permitir acceso a la propia página de mantenimiento y archivos estáticos/media
            if path == maintenance_url or path.startswith(('/static/', '/media/', '/favicon.ico')):
                return self.get_response(request)

            # Opcional: Permitir acceso al admin incluso en mantenimiento para poder arreglar cosas
            if path.startswith('/admin'):
                return self.get_response(request)

            # Redirigir all lo demás a la página de mantenimiento
            return redirect(maintenance_url)

        return self.get_response(request)
