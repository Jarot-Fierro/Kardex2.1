from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView
from django.views.generic import TemplateView

from core.history import GenericHistoryListView
from core.mixin import DataTableMixin
from core.utils import IncludeUserFormCreate, IncludeUserFormUpdate
from establecimientos.forms.sectores import FormSector
from establecimientos.models.sectores import Sector

MODULE_NAME = 'Sectors'


class SectorListView(PermissionRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'sector/list.html'
    model = Sector
    datatable_columns = ['ID', 'Color', 'Establecimiento', 'Código', 'Observación', ]
    datatable_order_fields = ['id', 'color__nombre', 'establecimiento__nombre', 'codigo', 'observacion', ]
    datatable_search_fields = [
        'color__nombre__icontains',
        'establecimiento__nombre__icontains',
        'codigo__icontains',
        'observacion__icontains',
    ]

    permission_required = 'establecimiento.view_sector'
    raise_exception = True

    permission_view = 'establecimiento.view_sector'
    permission_update = 'establecimiento.change_sector'

    url_detail = 'sector_detail'
    url_update = 'sector_update'

    def render_row(self, obj):
        return {
            'ID': obj.id,
            'Código': (obj.codigo or '').upper(),
            'Color': (obj.color.nombre or '').upper(),
            'Observación': (obj.observacion or '').capitalize(),
            'Establecimiento': (obj.establecimiento.nombre or '').upper(),
        }

    def get_base_queryset(self):
        """Filtra por el establecimiento del usuario logueado."""
        user = getattr(self.request, 'user', None)
        establecimiento = getattr(user, 'establecimiento', None) if user else None
        qs = Sector.objects.filter(status=True)
        if establecimiento:
            return qs.filter(establecimiento=establecimiento)
        # Si el usuario no tiene establecimiento, no mostrar registros
        return qs.none()

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Sectores',
            'list_url': reverse_lazy('sector_list'),
            'create_url': reverse_lazy('sector_create'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'asc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context


class SectorDetailView(PermissionRequiredMixin, DetailView):
    model = Sector
    template_name = 'sector/detail.html'
    permission_required = 'establecimiento.view_sector'
    raise_exception = True

    def render_to_response(self, context, **response_kwargs):
        # Si es una solicitud AJAX, devolvemos solo el fragmento HTML
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class SectorCreateView(PermissionRequiredMixin, IncludeUserFormCreate, CreateView):
    template_name = 'sector/form.html'
    model = Sector
    form_class = FormSector
    success_url = reverse_lazy('sector_list')
    permission_required = 'establecimiento:add_sector'

    def form_valid(self, form):
        messages.success(self.request, 'Sector creado correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo Sector'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class SectorUpdateView(PermissionRequiredMixin, IncludeUserFormUpdate, UpdateView):
    template_name = 'sector/form.html'
    model = Sector
    form_class = FormSector
    success_url = reverse_lazy('sector_list')
    permission_required = 'change_sector'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.info(self.request, 'Sector actualizado correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Sector'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class SectorHistoryListView(GenericHistoryListView):
    base_model = Sector
    permission_required = 'establecimiento.view_sector'
    template_name = 'history/list.html'

    url_last_page = 'sector_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_last_page'] = self.url_last_page
        return context
