from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import *
from .models import Soporte


# === SOPORTE ===


@admin.register(Soporte)
class TicketAdmin(SimpleHistoryAdmin):
    list_display = ("id", "titulo", "estado", "creado_por",)
    search_fields = ("titulo", "descripcion",)
    ordering = ("-updated_at",)

    def has_delete_permission(self, request, obj=None):
        return False


# === COMUNA ===


# === ESTABLECIMIENTO ===
@admin.register(Establecimiento)
class EstablecimientoAdmin(SimpleHistoryAdmin):
    list_display = ("id", "nombre", "direccion", "telefono", "comuna")
    search_fields = ("nombre", "direccion", "comuna__nombre")
    autocomplete_fields = ("comuna",)
    ordering = ("-updated_at",)

    def has_delete_permission(self, request, obj=None):
        return False


# === FICHA ===
@admin.register(Ficha)
class FichaAdmin(SimpleHistoryAdmin):
    list_display = (
        "id",
        "numero_ficha_sistema",
        "numero_ficha_tarjeta",
        "paciente",
        "establecimiento",
        "pasivado",
        "sector",
    )
    search_fields = (
        "numero_ficha_sistema",
        "numero_ficha_tarjeta",
        "paciente__rut",
        "paciente__nombre",
        "paciente__apellido_paterno",
        'establecimiento__nombre'
    )
    list_filter = ("pasivado", "establecimiento")
    autocomplete_fields = ("paciente", "establecimiento", "usuario")
    ordering = ("-updated_at",)

    def has_delete_permission(self, request, obj=None):
        return False


# === MOVIMIENTO FICHA ===
@admin.register(MovimientoFicha)
class MovimientoFichaAdmin(SimpleHistoryAdmin):
    list_display = (
        "id",
        "ficha",
        "servicio_clinico_envio",
        "servicio_clinico_recepcion",
        "estado_envio",
        "estado_recepcion",
        "fecha_envio",
        "fecha_recepcion",
    )
    search_fields = (
        "ficha__id",
        "ficha__paciente__rut",
        "servicio_clinico_envio__nombre",
        "servicio_clinico_recepcion__nombre",
        "profesional_envio__nombres",
        "profesional_recepcion__nombres",
    )
    list_filter = ("estado_envio", "estado_recepcion", "fecha_envio", "fecha_recepcion")
    autocomplete_fields = (
        "ficha",
        "servicio_clinico_envio",
        "servicio_clinico_recepcion",
        "usuario_envio",
        "usuario_recepcion",
        "profesional_envio",
        "profesional_recepcion",
    )
    ordering = ("-updated_at",)

    def has_delete_permission(self, request, obj=None):
        return False
