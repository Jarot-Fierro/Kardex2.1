from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget
from simple_history.admin import SimpleHistoryAdmin

from establecimientos.models.establecimiento import Establecimiento
from personas.models.genero import Genero
from personas.models.prevision import Prevision
from personas.models.profesion import Profesion
from personas.models.profesionales import Profesional
from personas.models.usuario_anterior import UsuarioAnterior


# === PREVISIÓN ===
class PrevisionResource(resources.ModelResource):
    class Meta:
        model = Prevision
        import_id_fields = ['id']
        fields = ('id', 'nombre', 'codigo',)
        export_order = ('id', 'nombre', 'codigo',)
        skip_unchanged = True
        report_skipped = True


@admin.register(Prevision)
class PrevisionAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = PrevisionResource

    list_display = ("id", "nombre", "codigo")
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


class ProfesionalResource(resources.ModelResource):
    # Aquí el campo para importación/exportación del establecimiento usando su nombre
    establecimiento = fields.Field(
        column_name='establecimiento',
        attribute='establecimiento',
        widget=ForeignKeyWidget(Establecimiento, 'pk')
    )

    class Meta:
        model = Profesional
        import_id_fields = ['id']  # Para identificar registros al importar
        fields = ('id', 'establecimiento', 'rut', 'nombres', 'correo', 'telefono',)
        export_order = ('id', 'establecimiento', 'rut', 'nombres', 'correo', 'telefono',)
        skip_unchanged = True
        report_skipped = True


# === Admin final combinando historial + import/export ===
@admin.register(Profesional)
class ProfesionalAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = ProfesionalResource

    list_display = ("id", "rut", "nombres", "correo", "telefono", 'anexo', "profesion", "establecimiento")
    search_fields = ("rut", "nombres", "correo", "profesion__nombre", "establecimiento__nombre")
    autocomplete_fields = ("profesion", "establecimiento")
    list_filter = ("establecimiento",)
    ordering = ("-updated_at",)

    # Evitar borrado desde el admin
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


class UsuarioAnteriorResource(resources.ModelResource):
    establecimiento = fields.Field(
        column_name='establecimiento',
        attribute='establecimiento',
        widget=ForeignKeyWidget(Establecimiento, 'pk')
    )

    class Meta:
        model = UsuarioAnterior
        import_id_fields = ['id']
        fields = ('id', 'rut', 'nombre', 'correo', 'establecimiento',)
        export_order = ('id', 'rut', 'nombre', 'correo', 'establecimiento',)
        skip_unchanged = True
        report_skipped = True


@admin.register(UsuarioAnterior)
class UsuarioAnteriorAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = UsuarioAnteriorResource

    list_display = ("id", "rut", "nombre", "establecimiento", "correo",)
    search_fields = ("id", "rut", "nombre", "establecimiento__nombre", "correo",)
    autocomplete_fields = ("establecimiento",)
    list_filter = ("establecimiento",)
    ordering = ("-updated_at",)

    def has_delete_permission(self, request, obj=None):
        return False


import re
import datetime

from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import Widget
from simple_history.admin import SimpleHistoryAdmin

from personas.models.pacientes import Paciente
from personas.models.prevision import Prevision
from personas.models.usuario_anterior import UsuarioAnterior
from geografia.models.comuna import Comuna


# ==============================
# FUNCIONES DE LIMPIEZA
# ==============================
def limpiar_rut(valor):
    if not valor:
        return ''
    valor = str(valor).strip()
    valor = valor.replace('\xa0', '').replace('\u200b', '').replace(' ', '')
    valor = re.sub(r'[^0-9kK\.-]', '', valor)
    return valor.upper()


def es_rut_recien_nacido(rut):
    if not rut:
        return False
    rut_num = re.sub(r'[^\d]', '', rut.split('-')[0])
    return rut_num.isdigit() and int(rut_num) >= 90000000


def limpiar_texto(texto):
    if not texto:
        return ''
    texto = str(texto).strip()
    texto = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.upper()


def limpiar_telefono(valor):
    if not valor:
        return ''
    return re.sub(r'[^\d]', '', str(valor))


# ==============================
# MAPAS DE CONVERSIÓN
# ==============================
MAP_SEXO = {
    'M': 'MASCULINO',
    'F': 'FEMENINO',
}

MAP_ESTADO_CIVIL = {
    'S': 'SOLTERO',
    'C': 'CASADO',
    'D': 'DIVORCIADO',
    'V': 'VIUDO',
    'P': 'SEPARADO',
    'O': 'CONVIVIENTE',
}


# ==============================
# WIDGET FK CON CACHÉ
# ==============================
class CachedFKWidget(Widget):
    def __init__(self, cache):
        self.cache = cache

    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return None
        return self.cache.get(str(value))


# ==============================
# RESOURCE PACIENTE
# ==============================
class PacienteResource(resources.ModelResource):
    rut = fields.Field(column_name='rut', attribute='rut')

    comuna = fields.Field(column_name='comuna', attribute='comuna')
    prevision = fields.Field(column_name='prevision', attribute='prevision')
    usuario_anterior = fields.Field(column_name='usuario_anterior', attribute='usuario_anterior')

    class Meta:
        model = Paciente
        import_id_fields = ('rut',)
        skip_unchanged = True
        report_skipped = False

        use_bulk = True
        batch_size = 1000

        fields = (
            'rut',
            'id_anterior',
            'nombre',
            'apellido_paterno',
            'apellido_materno',
            'nombre_social',
            'sexo',
            'estado_civil',
            'fecha_nacimiento',
            'direccion',
            'numero_telefono1',
            'numero_telefono2',
            'ocupacion',
            'alergico_a',
            'recien_nacido',
            'extranjero',
            'fallecido',
            'fecha_fallecimiento',
            'comuna',
            'prevision',
            'usuario_anterior',
        )

    # ==========================
    # INIT CORRECTO (CRÍTICO)
    # ==========================
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._comunas = {str(c.codigo): c for c in Comuna.objects.all()}
        self._previsiones = {str(p.codigo): p for p in Prevision.objects.all()}
        self._usuarios_anteriores = {u.rut: u for u in UsuarioAnterior.objects.all()}

        self.fields['comuna'].widget = CachedFKWidget(self._comunas)
        self.fields['prevision'].widget = CachedFKWidget(self._previsiones)
        self.fields['usuario_anterior'].widget = CachedFKWidget(self._usuarios_anteriores)

    # ==========================
    # LIMPIEZA POR FILA
    # ==========================
    def before_import_row(self, row, **kwargs):

        row['rut'] = limpiar_rut(row.get('rut'))
        if es_rut_recien_nacido(row['rut']):
            raise Exception(f"RUT RN omitido: {row['rut']}")

        for campo in (
                'nombre', 'apellido_paterno', 'apellido_materno',
                'nombre_social', 'direccion', 'ocupacion', 'alergico_a'
        ):
            row[campo] = limpiar_texto(row.get(campo))

        row['numero_telefono1'] = limpiar_telefono(row.get('numero_telefono1'))
        row['numero_telefono2'] = limpiar_telefono(row.get('numero_telefono2'))

        sexo_raw = str(row.get('sexo', '')).strip().upper()
        row['sexo'] = MAP_SEXO.get(sexo_raw, sexo_raw)

        estado_raw = str(row.get('estado_civil', '')).strip().upper()
        row['estado_civil'] = MAP_ESTADO_CIVIL.get(estado_raw, 'NO INFORMADO')

        row['fecha_nacimiento'] = self._parse_fecha(row.get('fecha_nacimiento'))
        row['fecha_fallecimiento'] = self._parse_fecha(row.get('fecha_fallecimiento'))

    # ==========================
    # PARSER DE FECHAS
    # ==========================
    def _parse_fecha(self, valor):
        if not valor:
            return None

        if isinstance(valor, datetime.date):
            return valor

        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.datetime.strptime(str(valor), fmt).date()
            except ValueError:
                pass

        return None


# ==============================
# ADMIN PACIENTE
# ==============================
@admin.register(Paciente)
class PacienteAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = PacienteResource

    list_display = (
        'rut',
        'nombre',
        'apellido_paterno',
        'apellido_materno',
        'sexo',
        'estado_civil',
        'comuna',
        'prevision',
        'updated_at',
    )

    search_fields = (
        'rut',
        'nombre',
        'apellido_paterno',
        'apellido_materno',
    )

    list_filter = (
        'sexo',
        'estado_civil',
        'comuna',
        'prevision',
    )

    autocomplete_fields = (
        'comuna',
        'prevision',
        'usuario_anterior',
    )

    ordering = ('-updated_at',)

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    def has_delete_permission(self, request, obj=None):
        return False
