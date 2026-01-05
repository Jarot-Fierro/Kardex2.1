from django.shortcuts import redirect
from django.urls import reverse


from django.shortcuts import redirect
from django.urls import reverse


class EstablecimientoRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        path = request.path

        # 🔹 EXCLUIR ADMIN COMPLETO
        if path.startswith('/admin'):
            return self.get_response(request)

        # rutas que NO deben exigir establecimiento
        exempt_paths = [
            reverse('login'),
            reverse('logout'),
            reverse('no_establecimiento'),
        ]

        # Si no está autenticado, continuar normal
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Si la ruta está exenta, permitir
        if any(path.startswith(ep) for ep in exempt_paths):
            return self.get_response(request)

        # validar establecimiento
        if not getattr(request.user, 'establecimiento', None):
            return redirect('no_establecimiento')

        return self.get_response(request)

