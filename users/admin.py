from django.contrib.auth.admin import UserAdmin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget
from simple_history.admin import SimpleHistoryAdmin

from establecimientos.models.establecimiento import Establecimiento
from users.models import User


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

from users.models import Role

from django.contrib import admin

@admin.action(description="Asignar rol Clinico")
def asignar_clinico(modeladmin, request, queryset):
    rol = Role.objects.filter(role_name="clinico").first()

    if not rol:
        modeladmin.message_user(
            request,
            "El rol 'clinico' no existe",
            level="error"
        )
        return

    for user in queryset:
        user.rol = rol
        user.save()


@admin.action(description="Asignar rol Visualizador")
def asignar_visualizador(modeladmin, request, queryset):
    rol = Role.objects.filter(role_name="visualizador").first()

    if not rol:
        modeladmin.message_user(request, "El rol 'visualizador' no existe", level="error")
        return

    for user in queryset:
        user.rol = rol
        user.save()


@admin.action(description="Asignar rol Solo Movimientos Clinicos")
def asignar_movimientos(modeladmin, request, queryset):
    rol = Role.objects.filter(role_name="solo movimientos clinicos").first()

    if not rol:
        modeladmin.message_user(request, "El rol no existe", level="error")
        return

    for user in queryset:
        user.rol = rol
        user.save()


@admin.action(description="Asignar rol Administrador")
def asignar_administrador(modeladmin, request, queryset):
    rol = Role.objects.filter(role_name="administrador").first()

    if not rol:
        modeladmin.message_user(request, "El rol 'administrador' no existe", level="error")
        return

    for user in queryset:
        user.rol = rol
        user.save()


@admin.register(User)
class CustomUserAdmin(
    ImportExportModelAdmin,
    SimpleHistoryAdmin,
    UserAdmin
):
    resource_class = UserResource

    actions = [asignar_clinico, asignar_movimientos, asignar_visualizador, asignar_administrador]

    list_display = (
        'username',
        'rol',
        'first_name',
        'last_name',
        'establecimiento',
        'email',
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

    fieldsets = (
        ('Credenciales', {
            'fields': ('username', 'password'),
        }),
        ('Información personal', {
            'fields': ('first_name', 'last_name', 'email'),
        }),
        ('Información institucional', {
            'fields': ('rol', 'establecimiento'),
        }),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
        ('Auditoría', {
            'fields': ('last_login', 'date_joined'),
        }),
    )


@admin.action(description="Activar roles seleccionados")
def activar_roles(modeladmin, request, queryset):
    for role in queryset:
        role.status = True
        role.save()

    modeladmin.message_user(request, "Roles activados correctamente")


@admin.action(description="Desactivar roles seleccionados")
def desactivar_roles(modeladmin, request, queryset):
    for role in queryset:
        role.status = False
        role.save()

    modeladmin.message_user(request, "Roles desactivados correctamente")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):

    def estado_icono(self, obj):
        return obj.status

    estado_icono.boolean = True
    estado_icono.short_description = "Estado"

    list_display = (
        'role_name', 'usuarios', 'comunas', 'establecimientos', 'fichas', 'genero', 'movimiento_ficha', 'prevision',
        'profesion', 'profesionales', 'sectores', 'servicio_clinico', 'estado_icono',
    )
    search_fields = ('role_name',)

    actions = [activar_roles, desactivar_roles]



    fieldsets = (
        ("Información del Rol", {
            "fields": ("role_name", "establecimiento", "status",)
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
            "fields": ("paciente", "fichas", "movimiento_ficha", "movimiento_ficha_controlado"),
        }),
    )
