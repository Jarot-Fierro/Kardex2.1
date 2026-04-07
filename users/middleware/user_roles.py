from django.utils.deprecation import MiddlewareMixin


class UserRolesMiddleware(MiddlewareMixin):

    def process_request(self, request):
        user = getattr(request, 'user', None)

        # valores por defecto para evitar errores si no hay sesión
        request.user_roles = {}
        request.establecimiento = None

        if user and user.is_authenticated:
            # Establecimiento desde el usuario
            request.establecimiento = user.establecimiento

            # Traer rol asignado al usuario
            role = user.rol

            permisos = {
                "usuarios": 0,
                "comunas": 0,
                "establecimientos": 0,
                "fichas": 0,
                "genero": 0,
                "movimiento_ficha": 0,
                "movimiento_ficha_controlado": 0,
                "paciente": 0,
                "pais": 0,
                "prevision": 0,
                "profesion": 0,
                "colores_sector": 0,
                "profesionales": 0,
                "sectores": 0,
                "servicio_clinico": 0,
                "reportes": 0,
                "soporte": 0
            }

            # Si el usuario tiene un rol, obtener sus permisos
            if role:
                for perm in permisos.keys():
                    permisos[perm] = getattr(role, perm, 0)

            request.user_roles = permisos

        return None
