from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from establecimientos.models.colores import Color
from establecimientos.models.establecimiento import Establecimiento
from establecimientos.models.sectores import Sector
from establecimientos.models.servicio_clinico import ServicioClinico


@admin.register(Establecimiento)
class EstablecimientoAdmin(SimpleHistoryAdmin):
    list_display = ("id", "nombre", "direccion", "telefono", "comuna")
    search_fields = ("nombre", "direccion", "comuna__nombre")
    autocomplete_fields = ("comuna",)
    ordering = ("-updated_at",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ServicioClinico)
class ServicioClinicoAdmin(SimpleHistoryAdmin):
    list_display = ("id", "nombre", "tiempo_horas", "correo_jefe", "establecimiento")
    search_fields = ("nombre", "establecimiento__nombre")
    autocomplete_fields = ("establecimiento",)
    ordering = ("-updated_at",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Sector)
class SectorAdmin(SimpleHistoryAdmin):
    list_display = ("id", "codigo", "color", "establecimiento")
    search_fields = ("codigo", "color", "establecimiento")
    autocomplete_fields = ("establecimiento",)
    ordering = ("-updated_at",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Color)
class ColorAdmin(SimpleHistoryAdmin):
    list_display = ("id", "nombre",)
    search_fields = ("nombre",)
    ordering = ("-updated_at",)

    def has_delete_permission(self, request, obj=None):
        return False
