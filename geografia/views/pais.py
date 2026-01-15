from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView
from django.views.generic import TemplateView

from core.history import GenericHistoryListView
from core.mixin import DataTableMixin
from core.utils import IncludeUserFormCreate, IncludeUserFormUpdate
from geografia.forms.pais import FormPais
from geografia.models.pais import Pais

MODULE_NAME = 'Paises'


class PaisListView(DataTableMixin, TemplateView):
    template_name = 'pais/list.html'
    model = Pais
    datatable_columns = ['ID', 'Nombre', 'Código']
    datatable_order_fields = ['id', None, 'nombre', 'cod_pais']
    datatable_search_fields = ['nombre__icontains', 'cod_pais__icontains']

    url_detail = 'pais_detail'
    url_update = 'pais_update'

    def render_row(self, obj):
        return {
            'ID': obj.id,
            'Nombre': obj.nombre.upper(),
            'Código': (obj.cod_pais or ''),
        }

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Países',
            'list_url': reverse_lazy('pais_list'),
            'create_url': reverse_lazy('pais_create'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'asc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context


class PaisDetailView(DetailView):
    model = Pais
    template_name = 'pais/detail.html'

    def render_to_response(self, context, **response_kwargs):
        # Si es una solicitud AJAX, devolvemos solo el fragmento HTML
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class PaisCreateView(IncludeUserFormCreate, CreateView):
    template_name = 'pais/form.html'
    model = Pais
    form_class = FormPais
    success_url = reverse_lazy('pais_list')
    raise_exception = True

    def form_valid(self, form):
        messages.success(self.request, 'País creado correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo País'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class PaisUpdateView(IncludeUserFormUpdate, UpdateView):
    template_name = 'pais/form.html'
    model = Pais
    form_class = FormPais
    success_url = reverse_lazy('pais_list')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.info(self.request, 'Pais actualizado correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Pais'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class PaisHistoryListView(GenericHistoryListView):
    base_model = Pais
    template_name = 'history/list.html'

    url_last_page = 'pais_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_last_page'] = self.url_last_page
        return context
