from typing import Type, Optional

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpRequest
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from kardex.mixin import DataTableMixin


class GenericHistoryListView(PermissionRequiredMixin, DataTableMixin, TemplateView):
    """
    Vista genérica para listar históricos (django-simple-history) de cualquier modelo.

    Cómo usarla:
      - Crear una subclase indicando `base_model` (el modelo original con `.history`).
      - Opcionalmente ajustar `permission_required`, `template_name` y columnas.

    Ejemplo:
        from kardex.models import Pais

        class PaisHistoryListView(GenericHistoryListView):
            base_model = Pais
            permission_required = 'kardex.view_pais'
            template_name = 'kardex/history/list.html'

    La vista utilizará DataTableMixin para entregar datos a DataTables vía AJAX
    cuando la petición incluya el flag datatable (GET ?datatable=1) y el header
    "X-Requested-With: XMLHttpRequest".
    """

    template_name = 'kardex/history/list.html'

    # Modelo base (no el histórico). La subclase debe definirlo.
    base_model: Optional[Type] = None

    # Columnas por defecto para históricos
    datatable_columns = ['ID', 'Fecha', 'Usuario', 'Acción', 'Objeto']
    # Campos para ordenar (usamos nombres del modelo histórico)
    datatable_order_fields = ['history_id', None, 'history_date', 'history_user__username', 'history_type',
                              'history_change_reason']
    # Campos para buscar
    datatable_search_fields = [
        'history_user__username__icontains',
        'history_change_reason__icontains',
        # Búsqueda por representación string del objeto almacenada en get_object_str()
    ]

    # Permiso genérico; las subclases deberían establecerlo según su modelo
    permission_required = None
    raise_exception = True

    # URLs de acciones deshabilitadas por defecto para históricos (solo lectura)
    url_detail = None
    url_update = None
    url_delete = None

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        if not self.base_model:
            raise ValueError('Debe definir base_model en la subclase para usar GenericHistoryListView')
        # Resolver modelo histórico de django-simple-history
        try:
            history_model = self.base_model.history.model
        except Exception as e:
            raise ValueError(f'El modelo {self.base_model} no tiene históricos configurados: {e}')

        # DataTableMixin espera self.model
        self.model = history_model

        # Ajustar columnas si la subclase definió personalizadas
        # Nada especial aquí; DataTableMixin tomará self.datatable_columns
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Soporte para petición AJAX de DataTables
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_base_queryset(self):
        # Base queryset ordenado por fecha descendente
        qs = self.model.objects.all().select_related('history_user')
        return qs.order_by('-history_date')

    @staticmethod
    def _history_type_verbose(code: Optional[str]) -> str:
        mapping = {'+': 'Creado', '~': 'Actualizado', '-': 'Eliminado'}
        return mapping.get(code or '', code or '')

    def get_object_str(self, obj) -> str:
        # Mejor esfuerzo: intentar mostrar algo representativo del objeto
        # Primero intentamos el mé all instance si está disponible
        try:
            instance = getattr(obj, 'instance', None)
            if instance is not None:
                return str(instance)
        except Exception:
            pass
        # Fallback: combinar posibles campos comunes
        candidates = []
        for attr in ('nombre', 'codigo', 'id'):
            if hasattr(obj, attr):
                try:
                    val = getattr(obj, attr)
                    if val is not None:
                        candidates.append(str(val))
                except Exception:
                    pass
        return ' - '.join(candidates) or str(obj)

    def render_row(self, obj):
        return {
            'ID': getattr(obj, 'history_id', getattr(obj, 'id', None)),
            'Fecha': obj.history_date.strftime('%Y-%m-%d %H:%M:%S') if getattr(obj, 'history_date', None) else '',
            'Usuario': getattr(getattr(obj, 'history_user', None), 'username', '') or '',
            'Acción': self._history_type_verbose(getattr(obj, 'history_type', '')),
            'Motivo': getattr(obj, 'history_change_reason', '') or '',
            'Objeto': self.get_object_str(obj),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_name = getattr(self.base_model, '__name__', 'Objeto')
        context.update({
            'title': f'Histórico de {base_name}',
            'list_url': reverse_lazy(self.request.resolver_match.view_name) if hasattr(self.request,
                                                                                       'resolver_match') else '',
            'datatable_enabled': True,
            'datatable_order': [[0, 'desc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context
