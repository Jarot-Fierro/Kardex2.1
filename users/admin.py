from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import User, Role, UserRole


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'last_login')
    list_filter = ('is_staff', 'is_active', 'date_joined',)
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

    fieldsets = UserAdmin.fieldsets + (
        ('Información institucional', {
            'fields': (
                'establecimiento',
            ),
        }),
    )


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'role_id')
    list_filter = ('role_id',)
    search_fields = ('user_id__username', 'role_id__role_name')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        'role_name', 'comunas', 'establecimientos', 'fichas', 'genero', 'movimiento_ficha',
        'pais', 'prevision', 'profesion', 'profesionales', 'sectores', 'servicio_clinico', 'soporte'
    )
    search_fields = ('role_name',)

    fieldsets = (
        ("Información del Rol", {
            "fields": ("role_name",)
        }),

        ("Mantenedores", {
            "fields": (
                "pais", "sectores", "colores_sector", "profesion",
                "prevision", "genero"
            ),
        }),

        ("Gestión General del Sistema", {
            "fields": (
                "comunas", "establecimientos", "servicio_clinico",
                "profesionales", "soporte", "reportes"
            ),
        }),

        ("Sección Clínica", {
            "fields": ("paciente", "fichas", "movimiento_ficha"),
        }),
    )
