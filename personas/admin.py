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
    rut_num = re.sub(r'[^\d]', '', rut.split('-')[0] if '-' in rut else rut)
    return rut_num.isdigit() and int(rut_num) >= 90000000


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


# ==============================
# RESOURCE PACIENTE
# ==============================
class PacienteResource(resources.ModelResource):
    # Campos que necesitan widgets personalizados
    comuna = fields.Field(column_name='comuna', attribute='comuna')
    prevision = fields.Field(column_name='prevision', attribute='prevision')
    usuario_anterior = fields.Field(column_name='usuario_anterior', attribute='usuario_anterior')

    # Campos booleanos que necesitan limpieza especial
    recien_nacido = fields.Field(column_name='recien_nacido', attribute='recien_nacido')
    extranjero = fields.Field(column_name='extranjero', attribute='extranjero')
    fallecido = fields.Field(column_name='fallecido', attribute='fallecido')

    class Meta:
        model = Paciente
        import_id_fields = ('rut',)
        skip_unchanged = True
        report_skipped = True  # Cambiado a True para debug
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
            'nombres_padre',
            'nombres_madre',
            'nombre_pareja',
            'representante_legal',
            'pasaporte',
            'rut_madre',
        )

        export_order = fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Precargar datos en caché
        self._comunas = {str(c.codigo): c for c in Comuna.objects.all()}
        self._previsiones = {str(p.codigo): p for p in Prevision.objects.all()}
        self._usuarios_anteriores = {str(u.rut).strip(): u for u in UsuarioAnterior.objects.all()}

        # Asignar widgets con caché
        self.fields['comuna'].widget = CachedFKWidget(self._comunas, 'codigo')
        self.fields['prevision'].widget = CachedFKWidget(self._previsiones, 'codigo')
        self.fields['usuario_anterior'].widget = CachedFKWidget(self._usuarios_anteriores, 'rut')

    def before_import_row(self, row, **kwargs):
        """Limpieza previa de cada fila"""

        # Limpiar RUT
        rut_raw = row.get('rut', '').strip()
        row['rut'] = limpiar_rut(rut_raw)

        # Omitir recién nacidos
        if es_rut_recien_nacido(row['rut']):
            print(f"⚠️  Omitiendo RUT de recién nacido: {row['rut']}")
            return False  # Esto hace que django-import-export omita la fila

        # Limpiar campos de texto
        for campo in [
            'nombre', 'apellido_paterno', 'apellido_materno', 'nombre_social',
            'direccion', 'ocupacion', 'alergico_a', 'nombres_padre',
            'nombres_madre', 'nombre_pareja', 'representante_legal',
            'pasaporte', 'rut_madre'
        ]:
            row[campo] = limpiar_texto(row.get(campo, ''))

        # Limpiar teléfonos
        row['numero_telefono1'] = limpiar_telefono(row.get('numero_telefono1'))
        row['numero_telefono2'] = limpiar_telefono(row.get('numero_telefono2'))

        # Normalizar sexo
        sexo_raw = str(row.get('sexo', '')).strip().upper()
        row['sexo'] = MAP_SEXO.get(sexo_raw, 'FEMENINO' if sexo_raw == 'F' else 'MASCULINO')

        # Normalizar estado civil
        estado_raw = str(row.get('estado_civil', '')).strip().upper()
        row['estado_civil'] = MAP_ESTADO_CIVIL.get(estado_raw, 'NO INFORMADO')

        # Parsear fechas
        row['fecha_nacimiento'] = self._parse_fecha(row.get('fecha_nacimiento'))
        row['fecha_fallecimiento'] = self._parse_fecha(row.get('fecha_fallecimiento'))

        # Manejar valores booleanos
        row['recien_nacido'] = self._parse_booleano(row.get('recien_nacido'))
        row['extranjero'] = self._parse_booleano(row.get('extranjero'))
        row['fallecido'] = self._parse_booleano(row.get('fallecido'))

        # Limpiar ID anterior
        row['id_anterior'] = limpiar_entero(row.get('id_anterior'))

        # Manejar valores vacíos en campos FK
        row['comuna'] = self._parse_comuna(row.get('comuna'))
        row['prevision'] = self._parse_prevision(row.get('prevision'))
        row['usuario_anterior'] = self._parse_usuario_anterior(row.get('usuario_anterior'))

        return True

    def _parse_fecha(self, valor):
        """Parsear diferentes formatos de fecha"""
        if not valor:
            return None

        # Si ya es datetime.date
        if isinstance(valor, datetime.date):
            return valor

        # Si es datetime.datetime
        if isinstance(valor, datetime.datetime):
            return valor.date()

        valor_str = str(valor).strip()

        # Manejar fechas inválidas como 01-01-1900
        if valor_str in ['01-01-1900', '1900-01-01', '01/01/1900']:
            return None

        # Intentar diferentes formatos
        formatos = [
            "%Y-%m-%d",  # 2023-12-31
            "%d-%m-%Y",  # 31-12-2023
            "%d/%m/%Y",  # 31/12/2023
            "%Y/%m/%d",  # 2023/12/31
        ]

        for fmt in formatos:
            try:
                return datetime.datetime.strptime(valor_str, fmt).date()
            except ValueError:
                continue

        # Si no se pudo parsear, devolver None
        return None

    def _parse_booleano(self, valor):
        """Convertir diferentes representaciones a booleano"""
        if not valor:
            return False

        valor_str = str(valor).strip().lower()

        if valor_str in ['1', 'true', 't', 'yes', 'y', 'si', 'sí', 'verdadero']:
            return True
        elif valor_str in ['0', 'false', 'f', 'no', 'n', 'falso']:
            return False

        # Intentar convertir a int/float
        try:
            num_val = float(valor_str)
            return num_val != 0
        except (ValueError, TypeError):
            return False

    def _parse_comuna(self, valor):
        """Parsear código de comuna"""
        if not valor:
            return self._comunas.get('1')  # Valor por defecto

        valor_str = str(valor).strip()

        # Buscar por código exacto
        comuna = self._comunas.get(valor_str)

        if not comuna:
            print(f"⚠️  Comuna no encontrada: {valor_str}. Usando valor por defecto.")
            return self._comunas.get('1')

        return comuna

    def _parse_prevision(self, valor):
        """Parsear código de previsión"""
        if not valor:
            return None

        valor_str = str(valor).strip()

        # Buscar por código exacto
        prevision = self._previsiones.get(valor_str)

        if not prevision:
            print(f"⚠️  Previsión no encontrada: {valor_str}")
            return None

        return prevision

    def _parse_usuario_anterior(self, valor):
        """Parsear RUT de usuario anterior"""
        if not valor:
            return None

        valor_str = limpiar_rut(valor)

        # Buscar por RUT
        usuario = self._usuarios_anteriores.get(valor_str)

        if not usuario:
            print(f"⚠️  Usuario anterior no encontrado: {valor_str}")
            return None

        return usuario

    def skip_row(self, instance, original, row, import_validation_errors=None):
        """
        Lógica para saltar filas duplicadas
        """
        if Paciente.objects.filter(rut=instance.rut).exists():
            print(f"⚠️  Paciente ya existe: {instance.rut}")
            return True

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
        'comuna',
        'prevision',
        'fallecido',
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

    def has_delete_permission(self, request, obj=None):
        return False
