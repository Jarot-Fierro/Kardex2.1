from typing import Type, Optional, Set

from django.db import models
from django.http import HttpRequest
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView

from core.mixin import DataTableMixin


class GenericHistoryListView(DataTableMixin, TemplateView):
    """
    Vista genérica de historial con django-simple-history mejorada.
    Proporciona cambios legibles, manejo de FKs, choices, booleanos y exclusión de campos.
    """
    base_model: Optional[Type[models.Model]] = None

    # Campos técnicos que se excluyen del historial por defecto
    history_exclude_fields: Set[str] = {
        'created_at', 'updated_at', 'created_by', 'updated_by',
        'history_id', 'history_date', 'history_user', 'history_type', 'history_change_reason'
    }

    # Columnas para DataTable
    datatable_columns = ['ID', 'Fecha', 'Usuario', 'Acción', 'Objeto', 'Cambios']
    datatable_order_fields = ['history_id', None, 'history_date', 'history_user__username', 'history_type', None]
    datatable_search_fields = ['history_user__username__icontains', 'history_change_reason__icontains']

    url_detail = url_update = url_delete = None

    # ==============================================================
    # DISPATCH - configuramos el modelo histórico automáticamente
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
    # HELPERS DE RESOLUCIÓN DE DATOS
    # ==============================================================

    def _get_verbose_name(self, field_name: str) -> str:
        """Obtiene el verbose_name del campo en el modelo base."""
        try:
            return self.base_model._meta.get_field(field_name).verbose_name.capitalize()
        except:
            return field_name.replace('_', ' ').capitalize()

    def _get_field_display_value(self, field_name: str, value, record) -> str:
        """
        Resuelve el valor legible de un campo (FK, Choices, Boolean, etc.)
        """
        if value is None or value == "":
            return "—"

        try:
            field = self.base_model._meta.get_field(field_name)

            # 1. Manejo de Booleano
            if isinstance(field, (models.BooleanField, models.NullBooleanField)):
                return "Sí" if value else "No"

            # 2. Manejo de Choices
            if field.choices:
                return dict(field.choices).get(value, value)

            # 3. Manejo de ForeignKey / OneToOne
            if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                related_model = field.remote_field.model
                try:
                    # Intentamos obtener el objeto relacionado actual para usar su __str__
                    related_obj = related_model.objects.get(pk=value)
                    return str(related_obj)
                except related_model.DoesNotExist:
                    return f"ID {value} (Eliminado)"
                except:
                    return f"ID {value}"

        except:
            pass

        return str(value)

    def _get_user_display(self, user):
        if not user:
            return "Sistema / Script"
        name = f"{user.first_name} {user.last_name}".strip()
        return f"{name}" if name else user.username

    @staticmethod
    def _history_type_badge(code: Optional[str]) -> str:
        """Retorna un badge HTML según el tipo de acción."""
        badges = {
            '+': '<span class="badge badge-success">Creado</span>',
            '~': '<span class="badge badge-info">Modificado</span>',
            '-': '<span class="badge badge-danger">Eliminado</span>',
        }
        return mark_safe(badges.get(code, f'<span class="badge badge-secondary">{code}</span>'))

    # ==============================================================
    # 🔥 CAMBIOS DETALLADOS (REFACTORIZADO)
    # ==============================================================

    def _get_changes(self, obj) -> str:
        """
        Calcula y formatea los cambios entre el registro actual y el anterior.
        """
        # Si es creación, no comparamos (opcionalmente podríamos mostrar todos los campos iniciales)
        if obj.history_type == '+':
            return "<i>Registro inicial</i>"

        # Usamos prev_record que provee django-simple-history de forma eficiente
        previous = obj.prev_record
        if not previous:
            return "—"

        delta = obj.diff_against(previous)
        result = []

        for change in delta.changes:
            # Excluir campos técnicos
            if change.field in self.history_exclude_fields:
                continue

            field_label = self._get_verbose_name(change.field)
            old_val = self._get_field_display_value(change.field, change.old, previous)
            new_val = self._get_field_display_value(change.field, change.new, obj)

            # Solo agregar si el valor legible realmente cambió (evita ruido en FKs o campos procesados)
            if old_val != new_val:
                result.append(
                    format_html(
                        "<b>{}:</b> <span style='color:#d9534f; text-decoration:line-through;'>{}</span> "
                        "&rarr; <span style='color:#5cb85c; font-weight:bold;'>{}</span>",
                        field_label, old_val, new_val
                    )
                )

        return mark_safe("<br>".join(result)) if result else "—"

    # ==============================================================
    # Renderizado y Contexto
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
                    if val: return str(val)
                except:
                    pass
        return str(obj)

    def render_row(self, obj):
        return {
            'ID': getattr(obj, 'history_id', obj.id),
            'Fecha': obj.history_date.strftime('%Y-%m-%d %H:%M:%S') if obj.history_date else '',
            'Usuario': self._get_user_display(getattr(obj, 'history_user', None)),
            'Acción': self._history_type_badge(getattr(obj, 'history_type', '')),
            'Objeto': self.get_object_str(obj),
            'Cambios': self._get_changes(obj),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        nombre_modelo = getattr(self.base_model, '_meta', None)
        nombre = nombre_modelo.verbose_name_plural.capitalize() if nombre_modelo else 'Objetos'

        context.update({
            'title': f'Historial de {nombre}',
            'list_url': reverse_lazy(self.request.resolver_match.view_name),
            'datatable_enabled': True,
            'datatable_order': [[0, 'desc']],
            'datatable_page_length': 50,
            'columns': self.datatable_columns,
        })
        return context
