from django.shortcuts import redirect
from django.urls import reverse


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.path.startswith(('/static/', '/media/', '/favicon.ico')):
            return self.get_response(request)

        if request.user.is_authenticated:
            return self.get_response(request)

        if request.path not in ['/login/', '/admin/login/']:
            return redirect(reverse('login'))

        return self.get_response(request)
