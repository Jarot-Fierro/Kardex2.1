from django.utils.deprecation import MiddlewareMixin


class EstablecimientoMiddleware(MiddlewareMixin):
    """
    Middleware que adjunta el establecimiento del usuario autenticado al request
    para que esté disponible en todas las vistas.
    
    - Si el usuario está autenticado y tiene atributo `establecimiento`, se expone
      como `request.establecimiento`.
    - Si no está autenticado o no tiene establecimiento, `request.establecimiento`
      queda como None.
    """
    def process_request(self, request):
        user = getattr(request, 'user', None)
        establecimiento = None
        if user and user.is_authenticated:
            establecimiento = getattr(user, 'establecimiento', None)
        # Adjuntar siempre el atributo para evitar checks repetidos
        request.establecimiento = establecimiento
        return None
