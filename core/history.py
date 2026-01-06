from typing import Type, Optional

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpRequest
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from core.mixin import DataTableMixin


class GenericHistoryListView(PermissionRequiredMixin, DataTableMixin, TemplateView):
    """
    Vista genérica de historial con django-simple-history
    """
    base_model: Optional[Type] = None

    # Columnas para DataTable
    datatable_columns = ['ID', 'Fecha', 'Usuario', 'Acción', 'Objeto', 'Cambios']
    datatable_order_fields = ['history_id', None, 'history_date', 'history_user__username', 'history_type', None]
    datatable_search_fields = ['history_user__username__icontains', 'history_change_reason__icontains']

    permission_required = None
    raise_exception = True

    url_detail = url_update = url_delete = None

    # ==============================================================
    # DISPACH - configuramos el modelo histórico automáticamente
    # ==============================================================

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        if not self.base_model:
            raise ValueError("Debes definir base_model en la subclase Ej: base_model = Pais")

        try:
            self.model = self.base_model.history.model
        except Exception as e:
            raise ValueError(f'El modelo {self.base_model} no tiene histórico configurado: {e}')

        return super().dispatch(request, *args, **kwargs)

    # ==============================================================
    # GET AJAX / HTML
    # ==============================================================

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_base_queryset(self):
        return self.model.objects.all().select_related('history_user').order_by('-history_date')

    # ==============================================================
    # UTILIDAD - Nombre del usuario
    # ==============================================================

    def _get_user_display(self, user):
        if not user:
            return "Sistema / Script"
        name = f"{user.first_name} {user.last_name}".strip()
        return f"{user.username} ({name})" if name else user.username

    # ==============================================================
    # UTILIDAD - Acción legible
    # ==============================================================

    @staticmethod
    def _history_type_verbose(code: Optional[str]) -> str:
        return {'+': 'Creado', '~': 'Modificado', '-': 'Eliminado'}.get(code, code)

    # ==============================================================
    # 🔥 CAMBIOS DETALLADOS
    # ==============================================================

    def _get_changes(self, obj) -> str:
        if not hasattr(obj, 'diff_against'):
            return ""

        try:
            previous = obj.instance.history.filter(history_date__lt=obj.history_date).order_by('-history_date').first()
            if not previous:
                return "—"
        except:
            return "—"

        diff = obj.diff_against(previous)
        if not diff.changes:
            return "—"

        result = []
        for c in diff.changes:
            result.append(
                f"<b>{c.field}</b>: "
                f"<span style='color:red;'>{c.old}</span> → "
                f"<span style='color:green;'>{c.new}</span>"
            )
        return "<br>".join(result)

    # ==============================================================
    # Obtener nombre representativo del objeto
    # ==============================================================

    def get_object_str(self, obj):
        try:
            if obj.instance:
                return str(obj.instance)
        except:
            pass

        for field in ['nombre', 'codigo', 'descripcion', 'id']:
            if hasattr(obj, field):
                try:
                    val = getattr(obj, field)
                    if val:
                        return str(val)
                except:
                    pass

        return str(obj)

    # ==============================================================
    # Render fila para datatable
    # ==============================================================

    def render_row(self, obj):
        return {
            'ID': getattr(obj, 'history_id', obj.id),
            'Fecha': obj.history_date.strftime('%Y-%m-%d %H:%M:%S') if obj.history_date else '',
            'Usuario': self._get_user_display(getattr(obj, 'history_user', None)),
            'Acción': self._history_type_verbose(getattr(obj, 'history_type', '')),
            'Objeto': self.get_object_str(obj),
            'Cambios': self._get_changes(obj),
        }

    # ==============================================================
    # Contexto para plantilla
    # ==============================================================

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        nombre = getattr(self.base_model, '__name__', 'Objeto')
        context.update({
            'title': f'Historial de {nombre}',
            'list_url': reverse_lazy(self.request.resolver_match.view_name),
            'datatable_enabled': True,
            'datatable_order': [[0, 'desc']],
            'datatable_page_length': 50,
            'columns': self.datatable_columns,
        })
        return context
