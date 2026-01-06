from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import Ficha


@admin.register(Ficha)
class FichaAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    list_display = (
        "id",
        "numero_ficha_sistema",
        "numero_ficha_tarjeta",
        "paciente",
        "establecimiento",
        "sector",
        "pasivado",
        "created_at",
    )

    list_filter = (
        "pasivado",
        "establecimiento",
        "sector",
        "created_at",
    )

    search_fields = (
        "numero_ficha_sistema",
        "numero_ficha_tarjeta",
        "paciente__rut",
        "paciente__nombre",
        "paciente__apellido_paterno",
        "paciente__apellido_materno",
        "paciente__codigo",
    )

    autocomplete_fields = (
        "paciente",
        "usuario",
        "establecimiento",
        "sector",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "created_at",
        "updated_at",
        "fecha_creacion_anterior",
    )

    fieldsets = (
        ("Identificación de la ficha", {
            "fields": (
                "numero_ficha_sistema",
                "numero_ficha_tarjeta",
                "pasivado",
            )
        }),
        ("Paciente", {
            "fields": (
                "paciente",
            )
        }),
        ("Ubicación", {
            "fields": (
                "establecimiento",
                "sector",
            )
        }),
        ("Auditoría", {
            "fields": (
                "usuario",
                "fecha_mov",
                "fecha_creacion_anterior",
            )
        }),
        ("Observaciones", {
            "fields": (
                "observacion",
            )
        }),
        ("Sistema", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    def has_delete_permission(self, request, obj=None):
        # Igual que en Establecimiento: no permitir borrar fichas
        return False
