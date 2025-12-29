from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView
from django.views.generic import TemplateView

from core.history import GenericHistoryListView
from geografia.forms.comunas import FormComuna
from kardex.mixin import DataTableMixin
from kardex.models import Comuna

MODULE_NAME = 'Comunas'


class ComunaListView(PermissionRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'kardex/comuna/list.html'
    model = Comuna
    datatable_columns = ['ID', 'Nombre', 'Código']
    datatable_order_fields = ['id', None, 'nombre', 'codigo']
    datatable_search_fields = ['nombre__icontains', 'codigo__icontains']

    permission_required = 'kardex.view_comuna'
    raise_exception = True

    permission_view = 'kardex.view_comuna'
    permission_update = 'kardex.change_comuna'

    url_detail = 'kardex:comuna_detail'
    url_update = 'kardex:comuna_update'

    def render_row(self, obj):
        return {
            'ID': obj.id,
            'Nombre': obj.nombre.upper(),
            'Código': (obj.codigo or '').zfill(4),
        }

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Comunas',
            'list_url': reverse_lazy('kardex:comuna_list'),
            'create_url': reverse_lazy('kardex:comuna_create'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'asc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context


class ComunaDetailView(PermissionRequiredMixin, DetailView):
    model = Comuna
    template_name = 'kardex/comuna/detail.html'
    permission_required = 'kardex.view_comuna'
    raise_exception = True

    def render_to_response(self, context, **response_kwargs):
        # Si es una solicitud AJAX, devolvemos solo el fragmento HTML
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class ComunaCreateView(PermissionRequiredMixin, CreateView):
    template_name = 'kardex/comuna/form.html'
    model = Comuna
    form_class = FormComuna
    success_url = reverse_lazy('kardex:comuna_list')
    permission_required = 'kardex.add_comuna'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.save()
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.success(request, 'Comuna creada correctamente')
            return redirect(self.success_url)
        from django.contrib import messages
        messages.error(request, 'Hay errores en el formulario')
        self.object = None
        return self.render_to_response(self.get_context_data(form=form, open_modal=True))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nueva Comuna'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class ComunaUpdateView(PermissionRequiredMixin, UpdateView):
    template_name = 'kardex/comuna/form.html'
    model = Comuna
    form_class = FormComuna
    success_url = reverse_lazy('kardex:comuna_list')
    permission_required = 'kardex:change_comuna'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.save()
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.success(request, 'Comuna actualizada correctamente')
            return redirect(self.success_url)
        from django.contrib import messages
        messages.error(request, 'Hay errores en el formulario')
        return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Comuna'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class ComunaHistoryListView(GenericHistoryListView):
    base_model = Comuna
    permission_required = 'kardex.view_comuna'
    template_name = 'kardex/history/list.html'
