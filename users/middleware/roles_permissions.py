from django.utils.deprecation import MiddlewareMixin

from users.permissions import sync_user_permissions


class RolePermissionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            sync_user_permissions(request.user)
