# views.py

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
# views.py
from django.views.generic import TemplateView


@method_decorator(login_required, name='dispatch')
class TutorialesView(TemplateView):
    """
    Vista basada en clases con decorador de login_required
    """
    template_name = 'kardex/tutoriales/index.html'

    # Configuración adicional si la necesitas
    def get_context_data(self, **kwargs):
        """
        Puedes agregar datos dinámicos aquí si es necesario en el futuro
        """
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Tutoriales en Contrucción',
        })

        # Aquí puedes agregar datos dinámicos si eventualmente los necesitas
        # Por ejemplo: progreso del usuario, estadísticas, etc.

        # Ejemplo de datos que podrías agregar en el futuro:
        # context['usuario'] = self.request.user
        # context['fecha_acceso'] = timezone.now()

        return context


# Versión alternativa aún más simple:
class TutorialesSimpleView(TemplateView):
    """
    Versión aún más simple si no necesitas autenticación
    """
    template_name = 'kardex/tutoriales/index.html'
