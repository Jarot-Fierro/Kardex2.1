from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView
from django.views.generic import TemplateView

from core.history import GenericHistoryListView
from core.mixin import DataTableMixin
from core.utils import IncludeUserFormCreate, IncludeUserFormUpdate
from personas.forms.prevision import FormPrevision
from personas.models.prevision import Prevision

MODULE_NAME = 'Previsiones'


class PrevisionListView(PermissionRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'prevision/list.html'
    model = Prevision
    datatable_columns = ['ID', 'Nombre']
    datatable_order_fields = ['id', None, 'nombre']
    datatable_search_fields = ['nombre__icontains']

    permission_required = 'personas.view_prevision'
    raise_exception = True

    permission_view = 'personas.view_prevision'
    permission_update = 'personas.change_prevision'

    url_detail = 'prevision_detail'
    url_update = 'prevision_update'

    def render_row(self, obj):
        return {
            'ID': obj.id,
            'Nombre': obj.nombre.upper(),
        }

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Previsiones',
            'list_url': reverse_lazy('prevision_list'),
            'create_url': reverse_lazy('prevision_create'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'asc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context


class PrevisionDetailView(PermissionRequiredMixin, DetailView):
    model = Prevision
    template_name = 'prevision/detail.html'
    permission_required = 'personas.view_prevision'
    raise_exception = True

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class PrevisionCreateView(PermissionRequiredMixin, IncludeUserFormCreate, CreateView):
    template_name = 'prevision/form.html'
    model = Prevision
    form_class = FormPrevision
    success_url = reverse_lazy('prevision_list')
    permission_required = 'personas.add_prevision'
    raise_exception = True

    def form_valid(self, form):
        messages.success(self.request, 'Previsión creada correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nueva Previsión'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class PrevisionUpdateView(PermissionRequiredMixin, IncludeUserFormUpdate, UpdateView):
    template_name = 'prevision/form.html'
    model = Prevision
    form_class = FormPrevision
    success_url = reverse_lazy('prevision_list')
    permission_required = 'personas.change_prevision'
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.info(self.request, 'Previsión actualizada correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Previsión'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class PrevisionHistoryListView(GenericHistoryListView):
    base_model = Prevision
    permission_required = 'personas.view_prevision'
    template_name = 'history/list.html'

    url_last_page = 'prevision_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_last_page'] = self.url_last_page
        return context
