from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView, TemplateView

from core.history import GenericHistoryListView
from core.mixin import DataTableMixin
from core.utils import IncludeUserFormCreate, IncludeUserFormUpdate
from geografia.forms.comunas import FormComuna
from geografia.models.comuna import Comuna

MODULE_NAME = 'Comunas'


class ComunaListView(DataTableMixin, TemplateView):
    template_name = 'comuna/list.html'
    model = Comuna
    datatable_columns = ['ID', 'Nombre', ]
    datatable_search_fields = ['nombre', ]
    datatable_order_fields = ['id', 'nombre', ]

    datatable_only = ['id', 'nombre', ]

    url_detail = 'detail_comunas'
    url_update = 'update_comunas'

    def render_row(self, obj):
        return {
            'ID': obj.id,
            'Nombre': obj.nombre,
        }

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Comunas',
            'list_url': reverse_lazy('list_comunas'),
            'create_url': reverse_lazy('create_comunas'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'asc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context


class ComunaDetailView(DetailView):
    model = Comuna
    template_name = 'comuna/detail.html'

    def render_to_response(self, context, **response_kwargs):
        # Si es una solicitud AJAX, devolvemos solo el fragmento HTML
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class ComunaCreateView(IncludeUserFormCreate, CreateView):
    template_name = 'comuna/form.html'
    model = Comuna
    form_class = FormComuna
    success_url = reverse_lazy('list_comunas')

    def form_valid(self, form):
        messages.success(self.request, 'Comuna creada correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nueva Comuna'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class ComunaUpdateView(IncludeUserFormUpdate, UpdateView):
    template_name = 'comuna/form.html'
    model = Comuna
    form_class = FormComuna
    success_url = reverse_lazy('list_comunas')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.info(self.request, 'Comuna actualizada correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Comuna'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class ComunaHistoryListView(GenericHistoryListView):
    base_model = Comuna
    template_name = 'history/list.html'

    url_last_page = 'list_comunas'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_last_page'] = self.url_last_page
        return context
