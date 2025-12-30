from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView
from django.views.generic import TemplateView

from core.history import GenericHistoryListView
from core.mixin import DataTableMixin
from core.utils import IncludeUserFormCreate, IncludeUserFormUpdate
from establecimientos.forms.colores import FormColor
from establecimientos.models.colores import Color

MODULE_NAME = 'Colores'


class ColorListView(PermissionRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'color/list.html'
    model = Color
    datatable_columns = ['ID', 'Nombre', ]
    datatable_order_fields = ['id', None, 'nombre', ]
    datatable_search_fields = ['nombre__icontains', ]

    permission_required = 'geografia.view_color'
    raise_exception = True

    permission_view = 'geografia.view_color'
    permission_update = 'geografia.change_color'

    url_detail = 'color_detail'
    url_update = 'color_update'

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
            'title': 'Listado de Colores',
            'list_url': reverse_lazy('color_list'),
            'create_url': reverse_lazy('color_create'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'asc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context


class ColorDetailView(PermissionRequiredMixin, DetailView):
    model = Color
    template_name = 'color/detail.html'
    permission_required = 'geografia.view_color'
    raise_exception = True

    def render_to_response(self, context, **response_kwargs):
        # Si es una solicitud AJAX, devolvemos solo el fragmento HTML
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class ColorCreateView(PermissionRequiredMixin, IncludeUserFormCreate, CreateView):
    template_name = 'color/form.html'
    model = Color
    form_class = FormColor
    success_url = reverse_lazy('color_list')
    permission_required = 'add_color'
    raise_exception = True

    def form_valid(self, form):
        messages.success(self.request, 'Color creado correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo Color'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class ColorUpdateView(PermissionRequiredMixin, IncludeUserFormUpdate, UpdateView):
    template_name = 'color/form.html'
    model = Color
    form_class = FormColor
    success_url = reverse_lazy('color_list')
    permission_required = 'change_color'
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.info(self.request, 'Color actualizado correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Color'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class ColorHistoryListView(GenericHistoryListView):
    base_model = Color
    permission_required = 'geografia.view_color'
    template_name = 'history/list.html'

    url_last_page = 'color_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_last_page'] = self.url_last_page
        return context
