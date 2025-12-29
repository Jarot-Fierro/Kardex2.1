from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import LoginForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')

        else:
            messages.error(request, 'Credenciales Invalidas')

    else:
        form = LoginForm()

    return render(request, 'usuarios/auth/login.html',
                  {'form': form}
                  )


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Sesión Cerrada Con Éxito')
