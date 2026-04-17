from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.timezone import localtime
from django.views.generic import DetailView
from django.views.generic import TemplateView

from core.mixin import DataTableMixin
from respaldos.models.respaldo_movimiento import RespaldoMovimientoMonologoControlado

MODULE_NAME = 'RespaldoMovimientos'


class RespaldoMovimientosListView(DataTableMixin, TemplateView):
    template_name = 'respaldo_movimientos/list.html'
    model = RespaldoMovimientoMonologoControlado
    datatable_columns = ['ID', 'Establecimiento', 'N° Ficha', 'Estado', 'Eliminado por', 'Fecha']
    datatable_order_fields = ['id', 'establecimiento__nombre', 'rut_paciente__nombre', 'numero_ficha', 'estado', 'usuario_eliminacion__username']
    datatable_search_fields = ['numero_ficha__icontains', 'rut__icontains']

    url_detail = 'respaldo_movimientos_detail'

    def get_url_update(self):
        return None

    def render_row(self, obj):
        fecha_local = localtime(obj.created_at)
        return {
            'ID': obj.id,
            'Establecimiento': obj.establecimiento.nombre if obj.establecimiento else 'N/A',
            'N° Ficha': obj.numero_ficha,
            'Estado': obj.get_estado_display(),
            'Eliminado por': obj.usuario_eliminacion.username if obj.usuario_eliminacion else 'N/A',
            'Fecha': fecha_local.strftime('%d/%m/%Y %H:%M:%S')
        }

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Respaldos de Movimientos',
            'list_url': reverse_lazy('respaldo_movimientos_list'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'desc']],
            'datatable_page_length': 25,
            'columns': self.datatable_columns,
        })
        return context


class RespaldoMovimientosDetailView(DetailView):
    model = RespaldoMovimientoMonologoControlado
    template_name = 'respaldo_movimientos/detail.html'
    permission_required = 'respaldos.view_respaldomovimientomonologocontrolado'

    def render_to_response(self, context, **response_kwargs):
        # Si es una solicitud AJAX, devolvemos solo el fragmento HTML
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


