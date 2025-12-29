# kardex/views/tickets.py

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import TemplateView

from kardex.forms.soporte import SoporteForm
from kardex.mixin import DataTableMixin
from kardex.models import Soporte


class TicketCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView
):
    model = Soporte
    form_class = SoporteForm
    template_name = 'kardex/soporte/ticket_form.html'

    # redirige a crear nuevo ticket o listado si quieres
    success_url = reverse_lazy('kardex:ticket_create')

    permission_required = 'kardex.add_soporte'
    raise_exception = True

    def form_valid(self, form):
        user = self.request.user

        if not user.establecimiento:
            raise PermissionDenied("El usuario no tiene establecimiento asignado.")

        ticket = form.save(commit=False)
        ticket.creado_por = user
        ticket.establecimiento = user.establecimiento
        ticket.save()

        messages.success(self.request, '✅ Ticket creado correctamente')
        return super().form_valid(form)


class SoporteListView(PermissionRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'kardex/soporte/lista.html'
    model = Soporte

    datatable_columns = [
        'ID',
        'Título',
        'Categoría',
        'Prioridad',
        'Estado',
        'Establecimiento',
        'Creado por',
        'Fecha creación',
    ]

    datatable_order_fields = [
        'id',
        'titulo',
        'categoria',
        'prioridad',
        'estado',
        'establecimiento__nombre',
        'creado_por__username',
        'created_at',
    ]

    datatable_search_fields = [
        'titulo__icontains',
        'descripcion__icontains',
        'categoria__icontains',
        'prioridad__icontains',
        'estado__icontains',
        'establecimiento__nombre__icontains',
        'creado_por__username__icontains',
    ]

    permission_required = 'kardex.view_soporte'
    raise_exception = True
    permission_view = 'kardex.view_soporte'

    # ✅ CLAVE: anular acciones del mixin
    def get_actions(self, obj):
        return ""

    def get_base_queryset(self):
        print(self.request.user)
        return Soporte.objects.filter(creado_por=self.request.user)

    def render_row(self, obj):
        creado_por = obj.creado_por
        full_name = creado_por.get_full_name() if creado_por and creado_por.get_full_name() else creado_por.username

        return {
            'ID': obj.id,
            'Título': obj.titulo,
            'Categoría': obj.get_categoria_display(),
            'Prioridad': obj.get_prioridad_display(),
            'Estado': obj.get_estado_display(),
            'Establecimiento': obj.establecimiento.nombre if obj.establecimiento else '-',
            'Creado por': full_name if creado_por else '-',
            'Fecha creación': obj.created_at.strftime('%d-%m-%Y %H:%M'),
        }

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Mis tickets de soporte',
            'datatable_enabled': True,
            'datatable_order': [[0, 'desc']],
            'datatable_page_length': 50,
            'columns': self.datatable_columns,
        })
        return context
