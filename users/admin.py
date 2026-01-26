from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget
from simple_history.admin import SimpleHistoryAdmin

from establecimientos.models.establecimiento import Establecimiento
from users.models import User, Role, UserRole


class UserResource(resources.ModelResource):
    establecimiento = fields.Field(
        column_name='establecimiento_id',
        attribute='establecimiento',
        widget=ForeignKeyWidget(Establecimiento, 'id')
    )

    class Meta:
        model = User
        import_id_fields = ('username',)
        fields = (
            'username',
            'is_superuser',
            'first_name',
            'last_name',
            'email',
            'is_staff',
            'is_active',
            'establecimiento',
        )
        skip_unchanged = True
        report_skipped = True
        use_transactions = True

    def before_import_row(self, row, **kwargs):
        for field in ['username', 'first_name', 'last_name', 'email']:
            value = row.get(field)
            if value is None:
                row[field] = ''
            elif isinstance(value, str):
                row[field] = value.strip()

    def after_save_instance(self, instance, *args, **kwargs):
        """
        FIRMA UNIVERSAL
        Compatible con django-import-export 4.3.14
        """
        dry_run = kwargs.get('dry_run', False)

        if dry_run:
            return

        if not instance.has_usable_password():
            instance.set_password('some')
            instance.save(update_fields=['password'])


# =========================
# ADMIN
# =========================
@admin.register(User)
class CustomUserAdmin(
    ImportExportModelAdmin,
    SimpleHistoryAdmin,
    UserAdmin
):
    resource_class = UserResource

    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'establecimiento',
        'is_staff',
        'is_active',
        'last_login',
    )

    list_filter = (
        'is_staff',
        'is_active',
        'establecimiento',
        'date_joined',
    )

    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
    )

    ordering = ('username',)

    fieldsets = UserAdmin.fieldsets + (
        ('Información institucional', {
            'fields': ('establecimiento',),
        }),
    )

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'role_id')
    list_filter = ('role_id',)
    search_fields = ('user_id__username', 'role_id__role_name')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        'role_name', 'usuarios', 'comunas', 'establecimientos', 'fichas', 'genero', 'movimiento_ficha',
        'pais', 'prevision', 'profesion', 'profesionales', 'sectores', 'servicio_clinico', 'soporte'
    )
    search_fields = ('role_name',)

    fieldsets = (
        ("Información del Rol", {
            "fields": ("role_name", "establecimiento",)
        }),

        ("Mantenedores", {
            "fields": (
                "pais", "sectores", "colores_sector", "profesion",
                "prevision", "genero"
            ),
        }),

        ("Gestión General del Sistema", {
            "fields": (
                "usuarios", "comunas", "establecimientos", "servicio_clinico",
                "profesionales", "soporte", "reportes"
            ),
        }),

        ("Sección Clínica", {
            "fields": ("paciente", "fichas", "movimiento_ficha"),
        }),
    )
