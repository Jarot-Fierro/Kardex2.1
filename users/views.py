from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.generic import CreateView

from core.mixin import DataTableMixin
from .forms import LoginForm, FormUsuario
from .models import User, UserRole

MODULE_NAME = 'Usuarios'


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
        form = LoginForm()

    return render(request, 'usuarios/auth/login.html',
                  {'form': form}
                  )


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Sesión Cerrada Con Éxito')
    return redirect('login')


from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model

User = get_user_model()


class UserListView(PermissionRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'usuarios/list.html'
    model = User

    datatable_columns = ['ID', 'Usuario', 'Nombre', 'Correo', 'Establecimiento', 'Último inicio']

    datatable_order_fields = [
        'user_id', 'username', 'first_name', 'email',
        'establecimiento__nombre', 'last_login'
    ]

    datatable_search_fields = [
        'username__icontains', 'first_name__icontains', 'last_name__icontains',
        'email__icontains', 'establecimiento__nombre__icontains'
    ]

    permission_required = 'auth.view_user'
    raise_exception = True

    url_detail = 'usuario_detail'
    url_update = 'usuario_update'

    # FILTRA SOLO USUARIOS DEL MISMO ESTABLECIMIENTO QUE EL USUARIO LOGUEADO
    def get_base_queryset(self):
        user = self.request.user

        if user.establecimiento:
            return User.objects.filter(
                establecimiento=user.establecimiento,
                is_active=True
            ).select_related('establecimiento')

        return User.objects.none()

    def render_row(self, obj):
        nombre = f"{obj.first_name or ''} {obj.last_name or ''}".strip()

        return {
            'ID': obj.user_id,  # << tu PK real
            'Usuario': obj.username,
            'Nombre': nombre if nombre else '—',
            'Correo': obj.email or '—',
            'Establecimiento': obj.establecimiento.nombre if obj.establecimiento else '—',
            'Último inicio': obj.last_login.strftime('%d-%m-%Y %H:%M') if obj.last_login else 'Nunca',
        }

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Usuarios del Establecimiento',
            'list_url': reverse_lazy('usuario_list'),
            'create_url': reverse_lazy('usuario_create'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'asc']],
            'datatable_page_length': 50,
            'columns': self.datatable_columns,
        })
        return context


class UserCreateView(PermissionRequiredMixin, CreateView):
    template_name = 'usuarios/creacion_usuario.html'
    model = User
    form_class = FormUsuario
    success_url = reverse_lazy('usuario_list')

    permission_required = 'auth.view_user'
    raise_exception = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request

        return kwargs

    @transaction.atomic  # <<<< Se asegura de que si algo falla, nada se guarda
    def form_valid(self, form):
        # Validación de establecimiento
        if not self.request.user.establecimiento:
            messages.error(self.request, "No tienes establecimiento asignado.")
            return redirect('no_establecimiento')

        # Asignar el establecimiento al usuario que se creará
        form.instance.establecimiento = self.request.user.establecimiento

        # Crear usuario
        user = form.save()

        # Crear relación en UserRole
        UserRole.objects.create(
            user_id=user,
            role_id=form.cleaned_data['roles']
        )

        messages.success(self.request, "Usuario registrado correctamente.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Nuevo Usuario para {self.request.user.establecimiento.nombre}'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context
