from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView
from django.views.generic import TemplateView

from core.history import GenericHistoryListView
from core.mixin import DataTableMixin
from core.utils import IncludeUserFormCreate, IncludeUserFormUpdate
from establecimientos.forms.servicio_clinico import FormServicioClinico
from establecimientos.models.servicio_clinico import ServicioClinico

MODULE_NAME = 'Servicios Clínicos'


class ServicioClinicoListView(PermissionRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'servicio_clinico/list.html'
    model = ServicioClinico
    datatable_columns = ['ID', 'Nombre', 'Jefe Área', 'Teléfono', 'Establecimiento']
    datatable_order_fields = ['id', None, 'nombre', 'correo_jefe', 'telefono',
                              'establecimiento__nombre']
    datatable_search_fields = ['nombre__icontains', 'correo_jefe__icontains',
                               'telefono__icontains', 'establecimiento__nombre__icontains']

    permission_required = 'establecimiento.view_servicioclinico'
    raise_exception = True

    permission_view = 'establecimiento.view_servicioclinico'
    permission_update = 'establecimiento.change_servicioclinico'

    url_detail = 'servicio_clinico_detail'
    url_update = 'servicio_clinico_update'

    def get_base_queryset(self):
        """Filtra por el establecimiento del usuario logueado."""
        user = getattr(self.request, 'user', None)
        establecimiento = getattr(user, 'establecimiento', None) if user else None
        qs = ServicioClinico.objects.all()
        if establecimiento:
            return qs.filter(establecimiento=establecimiento)
        # Si el usuario no tiene establecimiento, no mostrar registros
        return qs.none()

    def render_row(self, obj):
        return {
            'ID': obj.id,
            'Nombre': (obj.nombre or '').upper(),
            'Jefe Área': (obj.correo_jefe or ''),
            'Teléfono': (obj.telefono or ''),
            'Establecimiento': (obj.establecimiento.nombre or '').upper(),
        }

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Servicios Clínicos',
            'list_url': reverse_lazy('servicio_clinico_list'),
            'create_url': reverse_lazy('servicio_clinico_create'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'asc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context


class ServicioClinicoDetailView(PermissionRequiredMixin, DetailView):
    model = ServicioClinico
    template_name = 'servicio_clinico/detail.html'
    permission_required = 'establecimiento.view_servicio_clinico'
    raise_exception = True

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class ServicioClinicoCreateView(PermissionRequiredMixin, IncludeUserFormCreate, CreateView):
    template_name = 'servicio_clinico/form.html'
    model = ServicioClinico
    form_class = FormServicioClinico
    success_url = reverse_lazy('servicio_clinico_list')
    permission_required = 'establecimiento.add_servicio_clinico'
    raise_exception = True

    def form_valid(self, form):
        messages.success(self.request, 'Servicio Clínico creado correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo Servicio Clínico'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class ServicioClinicoUpdateView(PermissionRequiredMixin, IncludeUserFormUpdate, UpdateView):
    template_name = 'servicio_clinico/form.html'
    model = ServicioClinico
    form_class = FormServicioClinico
    success_url = reverse_lazy('servicio_clinico_list')
    permission_required = 'establecimiento.change_servicio_clinico'
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.info(self.request, 'Servicio Clínico actualizado correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Servicio Clínico'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class ServicioClinicoHistoryListView(GenericHistoryListView):
    base_model = ServicioClinico
    permission_required = 'establecimiento.view_servicio_clinico'
    template_name = 'history/list.html'

    url_last_page = 'servicio_clinico_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_last_page'] = self.url_last_page
        return context
