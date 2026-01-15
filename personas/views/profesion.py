from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView
from django.views.generic import TemplateView

from core.history import GenericHistoryListView
from core.mixin import DataTableMixin
from core.utils import IncludeUserFormCreate, IncludeUserFormUpdate
from personas.forms.profesiones import FormProfesion
from personas.models.profesion import Profesion

MODULE_NAME = 'Profesiones'


class ProfesionListView(DataTableMixin, TemplateView):
    template_name = 'profesion/list.html'
    model = Profesion
    datatable_columns = ['ID', 'Nombre']
    datatable_order_fields = ['id', None, 'nombre']
    datatable_search_fields = ['nombre__icontains']

    url_detail = 'profesion_detail'
    url_update = 'profesion_update'

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
            'title': 'Listado de Profesiones',
            'list_url': reverse_lazy('profesion_list'),
            'create_url': reverse_lazy('profesion_create'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'asc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context


class ProfesionDetailView(DetailView):
    model = Profesion
    template_name = 'profesion/detail.html'

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class ProfesionCreateView(IncludeUserFormCreate, CreateView):
    template_name = 'profesion/form.html'
    model = Profesion
    form_class = FormProfesion
    success_url = reverse_lazy('profesion_list')

    def form_valid(self, form):
        messages.success(self.request, 'Profesión creada correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nueva Profesión'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class ProfesionUpdateView(IncludeUserFormUpdate, UpdateView):
    template_name = 'profesion/form.html'
    model = Profesion
    form_class = FormProfesion
    success_url = reverse_lazy('profesion_list')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.info(self.request, 'Profesión actualizada correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Profesión'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class ProfesionHistoryListView(GenericHistoryListView):
    base_model = Profesion
    template_name = 'history/list.html'

    url_last_page = 'profesion_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_last_page'] = self.url_last_page
        return context
