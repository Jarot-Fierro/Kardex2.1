from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

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


# === PROFESIONAL ===
@admin.register(Profesional)
class ProfesionalAdmin(SimpleHistoryAdmin):
    list_display = ("id", "rut", "nombres", "correo", "telefono", "profesion", "establecimiento")
    search_fields = ("rut", "nombres", "correo", "profesion__nombre", "establecimiento__nombre")
    autocomplete_fields = ("profesion", "establecimiento")
    ordering = ("-updated_at",)

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
