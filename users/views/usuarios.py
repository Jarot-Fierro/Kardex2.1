from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import CreateView, DetailView
from django.views.generic import UpdateView

from core.mixin import DataTableMixin
from users.forms.usuarios import LoginForm, FormUsuario, FormUsuarioUpdate, UserResetPasswordForm, \
    FormUsuarioProfileUpdate
from users.models import User, UserRole

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


from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
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

    permission_view = 'auth.view_user'
    permission_update = 'auth.change_user'
    raise_exception = True

    url_update = 'usuarios_update'
    url_detail = 'usuarios_detail'

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
            'list_url': reverse_lazy('usuarios_list'),
            'create_url': reverse_lazy('usuarios_create'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'desc']],
            'datatable_page_length': 50,
            'columns': self.datatable_columns,
        })
        return context


class UserDetailView(PermissionRequiredMixin, DetailView):
    model = User
    template_name = 'usuarios/detail.html'
    permission_required = 'auth.view_user'
    raise_exception = True

    def render_to_response(self, context, **response_kwargs):
        # Si es una solicitud AJAX, devolvemos solo el fragmento HTML
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class UserCreateView(PermissionRequiredMixin, CreateView):
    template_name = 'usuarios/form.html'
    model = User
    form_class = FormUsuario
    success_url = reverse_lazy('usuarios_list')

    permission_required = 'auth.view_user'
    raise_exception = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request

        return kwargs

    @transaction.atomic
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


class UserUpdateView(PermissionRequiredMixin, UpdateView):
    template_name = 'usuarios/form.html'
    model = User
    form_class = FormUsuarioUpdate
    success_url = reverse_lazy('usuarios_list')

    permission_required = 'auth.view_user'
    raise_exception = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        # Validación de establecimiento
        if not self.request.user.establecimiento:
            messages.error(self.request, "No tienes establecimiento asignado.")
            return redirect('no_establecimiento')

        # Asegurarnos que el usuario se mantenga en el mismo establecimiento
        form.instance.establecimiento = self.request.user.establecimiento

        # Guardamos los cambios del usuario
        user = form.save()

        # Actualizamos la relación UserRole si cambió
        role_id = form.cleaned_data.get('roles')
        if role_id:
            UserRole.objects.update_or_create(
                user_id=user,
                defaults={'role_id': role_id}
            )

        messages.success(self.request, "Usuario actualizado correctamente.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Hay errores en el formulario.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Usuario de {self.request.user.establecimiento.nombre}'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class UserResetPasswordView(PermissionRequiredMixin, View):
    permission_required = 'auth.change_user'
    raise_exception = True
    template_name = 'usuarios/reset_password.html'

    def get(self, request, pk, *args, **kwargs):
        user = get_object_or_404(User, pk=pk)
        form = UserResetPasswordForm()
        return render(request, self.template_name, {'form': form, 'user_obj': user})

    def post(self, request, pk, *args, **kwargs):
        user = get_object_or_404(User, pk=pk)
        form = UserResetPasswordForm(request.POST)

        if form.is_valid():
            new_password = form.cleaned_data['password1']
            user.set_password(new_password)
            user.save()
            messages.info(request, f'Contraseña de {user.username} actualizada correctamente.')
            return redirect(reverse_lazy('usuarios_update', kwargs={'pk': user.pk}))

        return render(request, self.template_name, {'form': form, 'user_obj': user})


class UserProfileUpdateView(PermissionRequiredMixin, UpdateView):
    template_name = 'usuarios/perfil.html'
    model = User
    form_class = FormUsuarioProfileUpdate
    success_url = reverse_lazy('perfil')
    permission_required = 'auth.change_user'
    raise_exception = True

    def get_object(self, queryset=None):
        return self.request.user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request

        # Obtener rol actual del usuario
        try:
            current_user_role = UserRole.objects.get(user_id=self.request.user).role_id
        except UserRole.DoesNotExist:
            current_user_role = None

        kwargs['initial_role'] = current_user_role
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        form.instance.establecimiento = self.request.user.establecimiento
        user = form.save()

        # Actualizamos UserRole si cambió el rol
        role = form.cleaned_data.get('roles')
        if role:
            UserRole.objects.update_or_create(
                user_id=user,
                defaults={'role_id': role}
            )

        messages.info(self.request, "Tus datos se actualizaron correctamente.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Hay errores en el formulario.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar mis datos'
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class UserChangePasswordView(LoginRequiredMixin, View):
    """
    Permite al usuario logueado cambiar su propia contraseña.
    """
    login_url = 'login'
    template_name = 'usuarios/change_password.html'

    def get(self, request, *args, **kwargs):
        form = UserResetPasswordForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = UserResetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['password1']
            user = request.user
            user.set_password(new_password)
            user.save()
            messages.success(request, 'Tu contraseña se ha actualizado correctamente.')
            return redirect(reverse_lazy('usuarios_update', kwargs={'pk': request.user.pk}))

        return render(request, self.template_name, {'form': form})
