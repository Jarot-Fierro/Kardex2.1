from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView, CreateView, UpdateView, DetailView

from core.mixin import DataTableMixin
from users.forms.roles import RoleForm
from users.models import Role


class RoleListView(DataTableMixin, TemplateView):
    template_name = 'roles/list.html'
    model = Role
    datatable_columns = ['ID', 'Nombre del Rol', 'Establecimiento']
    datatable_search_fields = ['role_name', 'establecimiento__nombre']
    datatable_order_fields = ['rol_id', 'role_name', 'establecimiento__nombre']

    datatable_only = ['rol_id', 'role_name', 'establecimiento']

    permission_required = 'view_role'
    permission_view = 'roles.view_role'
    permission_update = 'roles.change_role'

    url_detail = 'roles_detail'
    url_update = 'roles_update'

    def render_row(self, obj):
        return {
            'ID': obj.rol_id,
            'Nombre del Rol': obj.role_name,
            'Establecimiento': obj.establecimiento.nombre if obj.establecimiento else '-',
        }

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Roles',
            'list_url': reverse_lazy('roles_list'),
            'create_url': reverse_lazy('create_roles'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'asc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context


class RoleCreateView(PermissionRequiredMixin, CreateView):
    template_name = 'roles/form.html'
    model = Role
    form_class = RoleForm
    success_url = reverse_lazy('roles_list')
    permission_required = 'roles.add_role'
    raise_exception = True

    def form_valid(self, form):
        messages.success(self.request, 'Rol creado correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo Rol'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context


class RoleUpdateView(PermissionRequiredMixin, UpdateView):
    template_name = 'roles/form.html'
    model = Role
    form_class = RoleForm
    success_url = reverse_lazy('roles_list')
    permission_required = 'roles.change_role'
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.info(self.request, 'Rol actualizado correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Rol'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context


class RoleDetailView(PermissionRequiredMixin, DetailView):
    model = Role
    template_name = 'roles/detail.html'
    permission_required = 'roles.view_role'
    raise_exception = True

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)
