from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView
from django.views.generic import TemplateView

from core.history import GenericHistoryListView
from core.mixin import DataTableMixin
from core.utils import IncludeUserFormCreate, IncludeUserFormUpdate
from personas.forms.genero import FormGenero
from personas.models.genero import Genero

MODULE_NAME = 'Generoes'


class GeneroListView(DataTableMixin, TemplateView):
    template_name = 'genero/list.html'
    model = Genero
    datatable_columns = ['ID', 'Nombre', ]
    datatable_order_fields = ['id', None, 'nombre', ]
    datatable_search_fields = ['nombre__icontains', ]

    url_detail = 'genero_detail'
    url_update = 'genero_update'

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
            'title': 'Listado de Generos',
            'list_url': reverse_lazy('genero_list'),
            'create_url': reverse_lazy('genero_create'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'asc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context


class GeneroDetailView(PermissionRequiredMixin, DetailView):
    model = Genero
    template_name = 'genero/detail.html'

    def render_to_response(self, context, **response_kwargs):
        # Si es una solicitud AJAX, devolvemos solo el fragmento HTML
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class GeneroCreateView(IncludeUserFormCreate, CreateView):
    template_name = 'genero/form.html'
    model = Genero
    form_class = FormGenero
    success_url = reverse_lazy('genero_list')

    def form_valid(self, form):
        messages.success(self.request, 'Genero creado correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo Genero'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class GeneroUpdateView(IncludeUserFormUpdate, UpdateView):
    template_name = 'genero/form.html'
    model = Genero
    form_class = FormGenero
    success_url = reverse_lazy('genero_list')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.info(self.request, 'Genero actualizado correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Genero'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class GeneroHistoryListView(GenericHistoryListView):
    base_model = Genero
    template_name = 'history/list.html'

    url_last_page = 'genero_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_last_page'] = self.url_last_page
        return context
