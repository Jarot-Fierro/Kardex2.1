from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import Ficha, MovimientoFicha


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
        "status_icon",
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
                "numero_ficha_respaldo",
                "pasivado",
                "status",
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
                "usuario_anterior",
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
                "created_by",
                "updated_by",
            )
        }),
    )

    def status_icon(self, obj):
        return obj.status

    status_icon.boolean = True
    status_icon.short_description = "Estado"


@admin.register(MovimientoFicha)
class MovimientoFichaAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    list_display = (
        "id",
        "ficha",
        "establecimiento",
        "estado_envio",
        "estado_recepcion",
        "estado_traspaso",
        "fecha_envio",
        "fecha_recepcion",
        "fecha_traspaso",
        "created_at",
    )

    list_filter = (
        "estado_envio",
        "estado_recepcion",
        "estado_traspaso",
        "establecimiento",
        "fecha_envio",
        "fecha_recepcion",
        "fecha_traspaso",
        "created_at",
    )

    search_fields = (
        "ficha__numero_ficha_sistema",
        "ficha__paciente__rut",
        "ficha__paciente__nombre",
        "ficha__paciente__apellido_paterno",
        "rut_anterior",
        "rut_anterior_profesional",
        "observacion_envio",
        "observacion_recepcion",
        "observacion_traspaso",
    )

    autocomplete_fields = (
        "ficha",
        "establecimiento",
        "servicio_clinico_envio",
        "servicio_clinico_recepcion",
        "servicio_clinico_traspaso",
        "usuario_envio",
        "usuario_recepcion",
        "usuario_traspaso",
        "profesional_envio",
        "profesional_recepcion",
        "profesional_traspaso",
    )

    ordering = ("-fecha_envio",)

    readonly_fields = (
        "created_at",
        "updated_at",
        "fecha_envio",
        "fecha_recepcion",
        "fecha_traspaso",
        "created_by",
        "updated_by",
    )

    fieldsets = (
        ("Ficha", {
            "fields": (
                "ficha",
                "establecimiento",
            )
        }),
        ("Envío", {
            "fields": (
                "estado_envio",
                "fecha_envio",
                "servicio_clinico_envio",
                "usuario_envio",
                "usuario_envio_anterior",
                "profesional_envio",
                "rut_anterior",
                "rut_anterior_profesional",
                "observacion_envio",
            )
        }),
        ("Recepción", {
            "fields": (
                "estado_recepcion",
                "fecha_recepcion",
                "servicio_clinico_recepcion",
                "usuario_recepcion",
                "usuario_recepcion_anterior",
                "profesional_recepcion",
                "observacion_recepcion",
            )
        }),
        ("Traspaso", {
            "fields": (
                "estado_traspaso",
                "fecha_traspaso",
                "servicio_clinico_traspaso",
                "usuario_traspaso",
                "profesional_traspaso",
                "observacion_traspaso",
            )
        }),
        ("Sistema", {
            "fields": (
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
            )
        }),
    )


from django.contrib import admin
from .models import MovimientoMonologoControlado


@admin.register(MovimientoMonologoControlado)
class MovimientoMonologoControladoAdmin(SimpleHistoryAdmin):
    list_display = (
        'id',
        'status_icon',
        'establecimiento',
        'rut',
        'rut_paciente',
        'numero_ficha',
        'servicio_clinico_destino',
        'estado',
        'fecha_salida',
        'fecha_entrada',
    )

    list_filter = (
        'estado',
        'establecimiento',
        'status',
    )

    search_fields = (
        'numero_ficha',
        'ficha__paciente__rut',
        'servicio_clinico_destino__nombre',
        'ficha__numero_ficha_sistema',
        'ficha__numero_ficha_tarjeta',
    )

    autocomplete_fields = (
        'rut_paciente',
        'ficha',
        'profesional',
        'establecimiento',
        'servicio_clinico_destino',
    )

    list_select_related = (
        'establecimiento',
        'rut_paciente',
        'ficha',
        'servicio_clinico_destino',
        'profesional',
    )

    ordering = ('-id',)

    readonly_fields = (
        'created_at',
        'updated_at',
        'created_by',
        'updated_by',
    )

    fieldsets = (
        ("Información General", {
            "fields": (
                "establecimiento",
                "rut",
                "rut_paciente",
                "numero_ficha",
                "ficha",
                "estado",
                "status",
            )
        }),

        ("Salida", {
            "fields": (
                "fecha_salida",
                "usuario_entrega",
                "usuario_entrega_id",
                "profesional",
                "profesional_anterior",
                "observacion_salida",
                "servicio_clinico_destino",
            )
        }),

        ("Entrada", {
            "fields": (
                "fecha_entrada",
                "usuario_entrada",
                "usuario_entrada_id",
                "observacion_entrada",
            )
        }),

        ("Traspaso", {
            "fields": (
                "fecha_traspaso",
                "usuario_traspaso",
                "observacion_traspaso",
            )
        }),

        ("Sistema", {
            "fields": (
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
            )
        }),
    )

    def status_icon(self, obj):
        return obj.status

    status_icon.boolean = True
    status_icon.short_description = "Estado"
