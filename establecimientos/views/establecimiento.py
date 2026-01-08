from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView
from django.views.generic import TemplateView

from core.history import GenericHistoryListView
from core.mixin import DataTableMixin
from core.utils import IncludeUserFormCreate, IncludeUserFormUpdate
from establecimientos.forms.establecimientos import FormEstablecimiento
from establecimientos.models.establecimiento import Establecimiento

MODULE_NAME = 'Establecimientos'


class EstablecimientoListView(PermissionRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'establecimiento/list.html'
    model = Establecimiento
    datatable_columns = ['ID', 'Nombre', 'Dirección', 'Teléfono', 'Comuna']
    datatable_order_fields = ['id', None, 'nombre', 'direccion', 'telefono', 'comuna__nombre']
    datatable_search_fields = ['nombre__icontains', 'direccion__icontains', 'telefono__icontains',
                               'comuna__nombre__icontains']

    permission_required = 'establecimientos.view_establecimiento'

    url_detail = 'establecimiento_detail'
    url_update = 'establecimiento_update'

    def render_row(self, obj):
        return {
            'ID': obj.id,
            'Nombre': obj.nombre.upper(),
            'Dirección': (obj.direccion or '').upper(),
            'Teléfono': (obj.telefono or ''),
            'Comuna': (obj.comuna.nombre or '').upper(),
        }

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Establecimientos',
            'list_url': reverse_lazy('establecimiento_list'),
            'create_url': reverse_lazy('establecimiento_create'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'asc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context


class EstablecimientoDetailView(PermissionRequiredMixin, DetailView):
    model = Establecimiento
    template_name = 'establecimiento/detail.html'
    permission_required = 'establecimientos.view_establecimiento'
    raise_exception = True

    def render_to_response(self, context, **response_kwargs):
        # Si es una solicitud AJAX, devolvemos solo el fragmento HTML
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class EstablecimientoCreateView(PermissionRequiredMixin, IncludeUserFormCreate, CreateView):
    template_name = 'establecimiento/form.html'
    model = Establecimiento
    form_class = FormEstablecimiento
    success_url = reverse_lazy('establecimiento_list')
    permission_required = 'establecimientos.add_establecimiento'

    def form_valid(self, form):
        messages.success(self.request, 'Comuna creada correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo Establecimiento'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class EstablecimientoUpdateView(PermissionRequiredMixin, IncludeUserFormUpdate, UpdateView):
    template_name = 'establecimiento/form.html'
    model = Establecimiento
    form_class = FormEstablecimiento
    success_url = reverse_lazy('establecimiento_list')
    permission_required = 'establecimientos.change_establecimiento'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, 'Comuna creada correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Establecimiento'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class EstablecimientoHistoryListView(GenericHistoryListView):
    base_model = Establecimiento
    permission_required = 'establecimientos.view_establecimiento'
    template_name = 'history/list.html'
