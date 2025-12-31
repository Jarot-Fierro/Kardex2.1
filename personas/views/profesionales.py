from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView
from django.views.generic import TemplateView

from core.history import GenericHistoryListView
from core.mixin import DataTableMixin
from core.utils import IncludeUserFormCreate, IncludeUserFormUpdate
from personas.forms.profesionales import FormProfesional
from personas.models.profesionales import Profesional

MODULE_NAME = 'Profesionales'


class ProfesionalListView(PermissionRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'profesional/list.html'
    model = Profesional
    datatable_columns = ['ID', 'RUT', 'Nombre', 'Correo', 'Teléfono', 'Anexo', 'Profesión', 'Establecimiento']
    datatable_order_fields = ['id', None, 'rut', 'nombres', 'correo', 'telefono', 'anexo', 'profesion__nombre',
                              'establecimiento__nombre']
    datatable_search_fields = [
        'rut__icontains', 'nombres__icontains', 'correo__icontains', 'telefono__icontains', 'anexo__icontains',
        'profesion__nombre__icontains', 'establecimiento__nombre__icontains'
    ]

    permission_required = 'personas.view_profesional'
    raise_exception = True

    permission_view = 'personas.view_profesional'
    permission_update = 'personas.change_profesional'

    url_detail = 'profesional_detail'
    url_update = 'profesional_update'

    def render_row(self, obj):
        return {
            'ID': obj.id,
            'RUT': obj.rut,
            'Nombre': (obj.nombres or '').upper(),
            'Correo': (obj.correo or ''),
            'Teléfono': (obj.telefono or ''),
            'Anexo': (obj.anexo or ''),
            'Profesión': (getattr(obj.profesion, 'nombre', '') or '').upper(),
            'Establecimiento': (getattr(obj.establecimiento, 'nombre', '') or '').upper(),
        }

    def get_base_queryset(self):
        """Filtra por el establecimiento del usuario logueado."""
        user = getattr(self.request, 'user', None)
        establecimiento = getattr(user, 'establecimiento', None) if user else None
        qs = Profesional.objects.filter(status=True)
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
            'title': 'Listado de Profesionales',
            'list_url': reverse_lazy('profesional_list'),
            'create_url': reverse_lazy('profesional_create'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'asc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context


class ProfesionalDetailView(PermissionRequiredMixin, DetailView):
    model = Profesional
    template_name = 'profesional/detail.html'
    permission_required = 'personas.view_profesionales'
    raise_exception = True

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class ProfesionalCreateView(PermissionRequiredMixin, IncludeUserFormCreate, CreateView):
    template_name = 'profesional/form.html'
    model = Profesional
    form_class = FormProfesional
    success_url = reverse_lazy('profesional_list')
    permission_required = 'personas.add_profesionales'
    raise_exception = True
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request

        return kwargs

    def form_valid(self, form):
        if not self.request.user.establecimiento:
            messages.error(self.request, "No tienes establecimiento asignado.")
            return redirect('no_establecimiento')
        form.instance.establecimiento = self.request.user.establecimiento
        messages.success(self.request, 'Profesional creado correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo Profesional'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class ProfesionalUpdateView(PermissionRequiredMixin, IncludeUserFormUpdate, UpdateView):
    template_name = 'profesional/form.html'
    model = Profesional
    form_class = FormProfesional
    success_url = reverse_lazy('profesional_list')
    permission_required = 'personas.change_profesionales'
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.info(self.request, 'Profesional actualizado correctamente')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Hay errores en el formulario')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Profesional'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class ProfesionalHistoryListView(GenericHistoryListView):
    base_model = Profesional
    permission_required = 'personas.view_profesional'
    template_name = 'history/list.html'

    url_last_page = 'profesional_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_last_page'] = self.url_last_page
        return context
