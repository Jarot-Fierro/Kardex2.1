from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView
from django.views.generic import TemplateView
from django.views.generic import UpdateView

from core.mixin import DataTableMixin
from users.forms.usuarios import LoginForm, FormUsuario, FormUsuarioUpdate, UserResetPasswordForm, \
    FormUsuarioProfileUpdate
from users.models import User

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


User = get_user_model()


class UserListView(DataTableMixin, TemplateView):
    template_name = 'usuarios/list.html'
    model = User

    datatable_columns = ['ID', 'RUT','Rol', 'Nombre', 'Correo', 'Establecimiento', 'Ultimo inicio']

    datatable_order_fields = [
        'user_id', None, 'username','rol', 'first_name', 'email',
        'establecimiento__nombre', 'last_login'
    ]

    datatable_search_fields = [
        'username__icontains','rol__role_name', 'first_name__icontains', 'last_name__icontains',
        'email__icontains', 'establecimiento__nombre__icontains'
    ]

    url_detail = 'usuarios_detail'

    def get_url_update(self):
        user = self.request.user
        if getattr(user, 'rol', None) and user.rol.usuarios == 2:
            return 'usuarios_update'
        return None

    # FILTRA SOLO USUARIOS DEL MISMO ESTABLECIMIENTO QUE EL USUARIO LOGUEADO
    def get_base_queryset(self):
        user = self.request.user

        qs = User.objects.select_related('establecimiento')

        # Si NO es superuser, filtramos por establecimiento
        if user.establecimiento:
            qs = qs.filter(establecimiento=user.establecimiento)
        else:
            return User.objects.none()

        # Opcional: si quieres excluir superusuarios del listado
        qs = qs.exclude(is_creator_system=True)

        return qs.order_by('first_name')

    def render_row(self, obj):
        nombre = f"{obj.first_name or ''} {obj.last_name or ''}".strip()

        last_login_str = 'Nunca'
        if obj.last_login:
            last_login_local = timezone.localtime(obj.last_login)
            last_login_str = last_login_local.strftime('%d-%m-%Y %H:%M')

        return {
            'ID': obj.user_id,  # << tu PK real
            'RUT': obj.username,
            'Rol': obj.rol.role_name if obj.rol else "",
            'Nombre': nombre if nombre else '—',
            'Correo': obj.email or '—',
            'Establecimiento': obj.establecimiento.nombre if obj.establecimiento else '—',
            'Ultimo inicio': last_login_str,
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
            'datatable_order': [[3, 'asc']],
            'datatable_page_length': 50,
            'columns': self.datatable_columns,
        })
        return context


class UserDetailView(DetailView):
    model = User
    template_name = 'usuarios/detail.html'

    def render_to_response(self, context, **response_kwargs):
        # Si es una solicitud AJAX, devolvemos solo el fragmento HTML
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class UserCreateView(CreateView):
    template_name = 'usuarios/form.html'
    model = User
    form_class = FormUsuario
    success_url = reverse_lazy('usuarios_list')

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


class UserUpdateView(UpdateView):
    template_name = 'usuarios/form.html'
    model = User
    form_class = FormUsuarioUpdate
    success_url = reverse_lazy('usuarios_list')

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


class UserResetPasswordView(View):
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


class UserProfileUpdateView(UpdateView):
    template_name = 'usuarios/perfil.html'
    model = User
    form_class = FormUsuarioProfileUpdate
    success_url = reverse_lazy('perfil')

    def get_object(self, queryset=None):
        return self.request.user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request

        # Obtener rol actual del usuario
        # try:
        #     current_user_role = UserRole.objects.get(user_id=self.request.user).role_id
        # except UserRole.DoesNotExist:
        #     current_user_role = None

        # kwargs['initial_role'] = current_user_role
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        form.instance.establecimiento = self.request.user.establecimiento
        user = form.save()

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
