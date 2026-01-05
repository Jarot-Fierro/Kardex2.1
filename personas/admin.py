from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget
from simple_history.admin import SimpleHistoryAdmin

from establecimientos.models.establecimiento import Establecimiento
from personas.models.genero import Genero
from personas.models.prevision import Prevision
from personas.models.profesion import Profesion
from personas.models.profesionales import Profesional
from personas.models.usuario_anterior import UsuarioAnterior


# === PREVISIÓN ===
@admin.register(Prevision)
class PrevisionAdmin(SimpleHistoryAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)
    ordering = ("-updated_at",)

    def has_delete_permission(self, request, obj=None):
        return False


# === PROFESIÓN ===
@admin.register(Profesion)
class ProfesionAdmin(SimpleHistoryAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)
    ordering = ("-updated_at",)

    def has_delete_permission(self, request, obj=None):
        return False


class ProfesionalResource(resources.ModelResource):
    # Aquí el campo para importación/exportación del establecimiento usando su nombre
    establecimiento = fields.Field(
        column_name='establecimiento',
        attribute='establecimiento',
        widget=ForeignKeyWidget(Establecimiento, 'pk')
    )

    class Meta:
        model = Profesional
        import_id_fields = ['id']  # Para identificar registros al importar
        fields = ('id', 'rut', 'nombres', 'correo', 'telefono', 'anexo', 'establecimiento')
        export_order = ('id', 'rut', 'nombres', 'correo', 'telefono', 'anexo', 'establecimiento')
        skip_unchanged = True
        report_skipped = True


# === Admin final combinando historial + import/export ===
@admin.register(Profesional)
class ProfesionalAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = ProfesionalResource

    list_display = ("id", "rut", "nombres", "correo", "telefono", 'anexo', "profesion", "establecimiento")
    search_fields = ("rut", "nombres", "correo", "profesion__nombre", "establecimiento__nombre")
    autocomplete_fields = ("profesion", "establecimiento")
    ordering = ("-updated_at",)

    # Evitar borrado desde el admin
    def has_delete_permission(self, request, obj=None):
        return False


# === Genero ===
@admin.register(Genero)
class GeneroAdmin(SimpleHistoryAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)
    ordering = ("-updated_at",)

    def has_delete_permission(self, request, obj=None):
        return False


# === USUARIO ANTERIOR ===
@admin.register(UsuarioAnterior)
class UsuarioAnteriorAdmin(SimpleHistoryAdmin):
    list_display = ("rut", "nombre", "correo", "establecimiento")
    search_fields = ("rut", "nombre", "correo", "establecimiento__nombre")
    autocomplete_fields = ("establecimiento",)
    ordering = ("-updated_at",)

    def has_delete_permission(self, request, obj=None):
        return False

# === PACIENTE ===
# @admin.register(Paciente)
# class PacienteAdmin(SimpleHistoryAdmin):
#     list_display = (
#         "id",
#         "codigo",
#         "rut",
#         "nombre",
#         "apellido_paterno",
#         "apellido_materno",
#         "comuna",
#         "prevision",
#         "fallecido",
#     )
#     search_fields = (
#         "codigo",
#         "rut",
#         "nip",
#         "nombre",
#         "apellido_paterno",
#         "apellido_materno",
#         "comuna__nombre",
#     )
#     list_filter = ("fallecido", "sexo", "estado_civil", "extranjero", "recien_nacido")
#     autocomplete_fields = ("comuna", "prevision", "usuario", "usuario_anterior")
#     ordering = ("-updated_at",)
#
#     def has_delete_permission(self, request, obj=None):
#         return False
