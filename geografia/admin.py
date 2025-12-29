from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.fields import Field
from simple_history.admin import SimpleHistoryAdmin

from geografia.models.comuna import Comuna
from geografia.models.pais import Pais


# Resource para exportar/importar
class ComunaResource(resources.ModelResource):
    class Meta:
        model = Comuna
        pais_nombre = Field(attribute='pais__nombre', column_name='Pais')
        import_id_fields = ['id']
        fields = ('id', 'nombre', 'codigo', 'pais_nombre')
        export_order = ('codigo', 'nombre',)
        skip_unchanged = True
        report_skipped = True


# Admin final integrando historial + import/export
@admin.register(Comuna)
class ComunaAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = ComunaResource

    list_display = ("id", "nombre", "codigo", "pais")
    search_fields = ("nombre", "codigo", "pais__nombre")
    ordering = ("-updated_at",)

    # opcional, como ya tenías
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Pais)
class PaisAdmin(SimpleHistoryAdmin):
    list_display = ("id", "nombre", "cod_pais")
    search_fields = ("nombre", "cod_pais")
    ordering = ("-updated_at",)

    def has_delete_permission(self, request, obj=None):
        return False
