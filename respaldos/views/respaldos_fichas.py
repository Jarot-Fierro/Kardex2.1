from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import DetailView
from django.views.generic import TemplateView

from core.mixin import DataTableMixin
from respaldos.models.respaldo_ficha import RespaldoFicha

MODULE_NAME = 'RespaldoFichas'


class RespaldoFichasListView(DataTableMixin, TemplateView):
    template_name = 'respaldo_fichas/list.html'
    model = RespaldoFicha
    datatable_columns = ['ID', 'N° Ficha Sistema', 'RUT',  'Eliminado por', 'Fecha']
    datatable_order_fields = ['id', 'numero_ficha_sistema', 'rut', 'usuario_eliminacion__username']
    datatable_search_fields = ['rut__icontains', 'numero_ficha_sistema__icontains']

    url_detail = 'respaldo_fichas_detail'

    def get_url_update(self):
        return None

    def render_row(self, obj):
        return {
            'ID': obj.id,
            'N° Ficha Sistema': obj.numero_ficha_sistema,
            'RUT': obj.rut,
            'Eliminado por': obj.usuario_eliminacion.username if obj.usuario_eliminacion else 'N/A',
            'Fecha': obj.created_at.strftime('%d/%m/%Y %H:%M:%S')
        }

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Respaldos de Fichas',
            'list_url': reverse_lazy('respaldo_fichas_list'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'desc']],
            'datatable_page_length': 25,
            'columns': self.datatable_columns,
        })
        return context


class RespaldoFichasDetailView(DetailView):
    model = RespaldoFicha
    template_name = 'respaldo_fichas/detail.html'
    permission_required = 'respaldos.view_respaldoficha'

    def render_to_response(self, context, **response_kwargs):
        # Si es una solicitud AJAX, devolvemos solo el fragmento HTML
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


