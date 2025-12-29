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


# === PROFESIONAL ===
@admin.register(Profesional)
class ProfesionalAdmin(SimpleHistoryAdmin):
    list_display = ("id", "rut", "nombres", "correo", "telefono", "profesion", "establecimiento")
    search_fields = ("rut", "nombres", "correo", "profesion__nombre", "establecimiento__nombre")
    autocomplete_fields = ("profesion", "establecimiento")
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
@admin.register(Paciente)
class PacienteAdmin(SimpleHistoryAdmin):
    list_display = (
        "id",
        "codigo",
        "rut",
        "nombre",
        "apellido_paterno",
        "apellido_materno",
        "comuna",
        "prevision",
        "fallecido",
    )
    search_fields = (
        "codigo",
        "rut",
        "nip",
        "nombre",
        "apellido_paterno",
        "apellido_materno",
        "comuna__nombre",
    )
    list_filter = ("fallecido", "sexo", "estado_civil", "extranjero", "recien_nacido")
    autocomplete_fields = ("comuna", "prevision", "usuario", "usuario_anterior")
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
