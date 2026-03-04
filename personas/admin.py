from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget, DateTimeWidget
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
        skip_unchanged = False
        report_skipped = False


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

from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import Widget
from simple_history.admin import SimpleHistoryAdmin

from personas.models.pacientes import Paciente
from personas.models.usuario_anterior import UsuarioAnterior
from core.utils.rut_ficticio import es_rut_recien_nacido
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


def limpiar_texto(texto):
    if not texto:
        return ''
    texto = str(texto).strip()
    # Permitir caracteres especiales necesarios (puntos, comas, números)
    texto = re.sub(r'[^\w\sáéíóúÁÉÍÓÚñÑ.,\-]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.upper()


def limpiar_telefono(valor):
    if not valor:
        return ''
    cleaned = re.sub(r'[^\d]', '', str(valor))
    return cleaned if cleaned else ''


def limpiar_entero(valor):
    """Limpia valores enteros, maneja '0' como None"""
    if not valor:
        return None
    try:
        num = int(float(str(valor).strip()))
        return num if num != 0 else None
    except (ValueError, TypeError):
        return None


# ==============================
# MAPAS DE CONVERSIÓN
# ==============================
MAP_SEXO = {
    'M': 'MASCULINO',
    'F': 'FEMENINO',
    'MASCULINO': 'MASCULINO',
    'FEMENINO': 'FEMENINO',
}

MAP_ESTADO_CIVIL = {
    'S': 'SOLTERO',
    'C': 'CASADO',
    'D': 'DIVORCIADO',
    'V': 'VIUDO',
    'P': 'SEPARADO',
    'O': 'CONVIVIENTE',
    'I': 'NO INFORMADO',
}


# ==============================
# WIDGET FK CON CACHÉ
# ==============================
class CachedFKWidget(Widget):
    def __init__(self, cache, campo_busqueda='codigo'):
        self.cache = cache
        self.campo_busqueda = campo_busqueda

    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return None
        valor_str = str(value).strip()

        # Buscar por el valor en el caché
        if self.campo_busqueda == 'codigo':
            # Para comuna y prevision buscamos por código
            return self.cache.get(valor_str)
        else:
            # Para usuario_anterior buscamos por RUT
            return self.cache.get(valor_str)

    def before_import_row(self, row, **kwargs):

        # Convertir fechas inválidas tipo 01-01-1900 0:00 a vacío
        for campo in ['fecha_nacimiento', 'fecha_fallecimiento']:
            valor = row.get(campo)
            if valor and '1900' in str(valor):
                row[campo] = None


# ==============================
# RESOURCE PACIENTE
# ==============================
class PacienteResource(resources.ModelResource):
    comuna = fields.Field(column_name='comuna', attribute='comuna')
    prevision = fields.Field(column_name='prevision', attribute='prevision')
    usuario_anterior = fields.Field(column_name='usuario_anterior', attribute='usuario_anterior')

    recien_nacido = fields.Field(column_name='recien_nacido', attribute='recien_nacido')
    extranjero = fields.Field(column_name='extranjero', attribute='extranjero')
    fallecido = fields.Field(column_name='fallecido', attribute='fallecido')

    class Meta:
        model = Paciente
        import_id_fields = ('rut',)
        skip_unchanged = False
        report_skipped = False
        use_bulk = True
        batch_size = 20000

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
            'nombres_padre',
            'nombres_madre',
            'nombre_pareja',
            'representante_legal',
            'pasaporte',
            'rut_madre',
        )

        export_order = fields

    # ✅ NUEVO: limpiar headers para evitar error de rut
    def before_import(self, dataset, **kwargs):
        dataset.headers = [h.strip().lower() for h in dataset.headers]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._comunas = {str(c.codigo): c for c in Comuna.objects.all()}
        self._previsiones = {str(p.codigo): p for p in Prevision.objects.all()}
        self._usuarios_anteriores = {str(u.rut).strip(): u for u in UsuarioAnterior.objects.all()}

        self.fields['comuna'].widget = CachedFKWidget(self._comunas, 'codigo')
        self.fields['prevision'].widget = CachedFKWidget(self._previsiones, 'codigo')
        self.fields['usuario_anterior'].widget = CachedFKWidget(self._usuarios_anteriores, 'rut')
        self.fields['fecha_nacimiento'].widget = DateTimeWidget(format='%d-%m-%Y %H:%M')
        self.fields['fecha_fallecimiento'].widget = DateTimeWidget(format='%d-%m-%Y %H:%M')

    def before_import_row(self, row, **kwargs):

        rut_raw = row.get('rut', '').strip()
        row['rut'] = limpiar_rut(rut_raw)

        if es_rut_recien_nacido(row['rut']):
            print(f"⚠️  Omitiendo RUT de recién nacido: {row['rut']}")
            return False

        for campo in [
            'nombre', 'apellido_paterno', 'apellido_materno', 'nombre_social',
            'direccion', 'ocupacion', 'alergico_a', 'nombres_padre',
            'nombres_madre', 'nombre_pareja', 'representante_legal',
            'pasaporte', 'rut_madre'
        ]:
            row[campo] = limpiar_texto(row.get(campo, ''))

        row['numero_telefono1'] = limpiar_telefono(row.get('numero_telefono1'))
        row['numero_telefono2'] = limpiar_telefono(row.get('numero_telefono2'))

        sexo_raw = str(row.get('sexo', '')).strip().upper()
        row['sexo'] = MAP_SEXO.get(sexo_raw, 'FEMENINO' if sexo_raw == 'F' else 'MASCULINO')

        estado_raw = str(row.get('estado_civil', '')).strip().upper()
        row['estado_civil'] = MAP_ESTADO_CIVIL.get(estado_raw, 'NO INFORMADO')

        row['fecha_nacimiento'] = row.get('fecha_nacimiento')
        row['fecha_fallecimiento'] = row.get('fecha_fallecimiento')

        row['recien_nacido'] = self._parse_booleano(row.get('recien_nacido'))
        row['extranjero'] = self._parse_booleano(row.get('extranjero'))
        row['fallecido'] = self._parse_booleano(row.get('fallecido'))

        row['id_anterior'] = limpiar_entero(row.get('id_anterior'))

        # ❌ ELIMINADO: no asignar FK manualmente
        # Dejamos que CachedFKWidget haga el trabajo

        return True

    def _parse_booleano(self, valor):
        if not valor:
            return False

        valor_str = str(valor).strip().lower()

        if valor_str in ['1', 'true', 't', 'yes', 'y', 'si', 'sí', 'verdadero']:
            return True
        elif valor_str in ['0', 'false', 'f', 'no', 'n', 'falso']:
            return False

        try:
            num_val = float(valor_str)
            return num_val != 0
        except (ValueError, TypeError):
            return False


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
        'id_anterior',
    )

    list_filter = (
        'sexo',
        'estado_civil',
        'prevision',
        'fallecido',
    )

    autocomplete_fields = (
        'comuna',
        'prevision',
        'usuario_anterior',
    )

    ordering = ('-id',)

    readonly_fields = (
        'created_at',
        'updated_at',
        'codigo',
    )

    fieldsets = (
        ('Identificación', {
            'fields': (
                'codigo',
                'rut',
                'id_anterior',
                'nombre',
                'apellido_paterno',
                'apellido_materno',
                'nombre_social',
                'pueblo_indigena',
            )
        }),
        ('Datos Personales', {
            'fields': (
                'sexo',
                'estado_civil',
                'fecha_nacimiento',
                'genero',
            )
        }),
        ('Datos Familiares', {
            'fields': (
                'nombres_padre',
                'nombres_madre',
                'nombre_pareja',
                'representante_legal',
                'rut_madre',
                'usar_rut_madre_como_responsable',
                'rut_responsable_temporal',
            )
        }),
        ('Contacto y Dirección', {
            'fields': (
                'direccion',
                'comuna',
                'numero_telefono1',
                'numero_telefono2',
                'sin_telefono',
                'ocupacion',
            )
        }),
        ('Estado y Previsión', {
            'fields': (
                'prevision',
                'recien_nacido',
                'extranjero',
                'fallecido',
                'fecha_fallecimiento',
                'pasaporte',
                'alergico_a',
            )
        }),
        ('Sistema', {
            'fields': (
                'usuario_anterior',
                'usuario',
                'created_by',
                'updated_by',
                'created_at',
                'updated_at',
            )
        }),
    )
