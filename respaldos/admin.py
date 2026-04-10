from django.contrib import admin

from .models.respaldo_ficha import RespaldoFicha
from .models.respaldo_movimiento import RespaldoMovimientoMonologoControlado
from .models.respaldo_paciente import RespaldoPaciente


# Register your models here.

@admin.register(RespaldoPaciente)
class RespaldoPacienteAdmin(admin.ModelAdmin):
    list_display = ('rut', 'nombre', 'apellido_paterno', 'apellido_materno', 'fecha_nacimiento', 'sexo', 'comuna', 'prevision', 'fallecido')
    search_fields = ('rut', 'nombre', 'apellido_paterno', 'apellido_materno', 'ficha', 'codigo')
    list_filter = ('sexo', 'estado_civil', 'fallecido', 'comuna', 'prevision', 'pueblo_indigena', 'extranjero')
    autocomplete_fields = ('comuna', 'prevision', 'genero', 'usuario', 'usuario_anterior', 'usuario_eliminacion')
    ordering = ('apellido_paterno', 'apellido_materno', 'nombre')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(RespaldoFicha)
class RespaldoFichaAdmin(admin.ModelAdmin):
    list_display = ('numero_ficha_sistema', 'rut', 'paciente', 'establecimiento', 'sector', 'pasivado', 'fecha_mov')
    search_fields = ('numero_ficha_sistema', 'rut', 'paciente__nombre', 'paciente__apellido_paterno', 'paciente__rut')
    list_filter = ('pasivado', 'establecimiento', 'sector', 'fecha_mov')
    autocomplete_fields = ('usuario', 'usuario_anterior', 'paciente', 'establecimiento', 'sector', 'usuario_eliminacion')
    ordering = ('-numero_ficha_sistema',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(RespaldoMovimientoMonologoControlado)
class RespaldoMovimientoAdmin(admin.ModelAdmin):
    list_display = ('establecimiento', 'rut', 'numero_ficha', 'estado', 'fecha_salida', 'fecha_entrada', 'profesional')
    search_fields = ('rut', 'numero_ficha', 'usuario_entrega', 'usuario_entrada', 'profesional_anterior')
    list_filter = ('estado', 'establecimiento', 'profesional', 'fecha_salida', 'fecha_entrada')
    autocomplete_fields = ('usuario_entrega_id', 'usuario_entrada_id', 'profesional', 'rut_paciente', 'establecimiento', 'ficha', 'servicio_clinico_destino', 'usuario_eliminacion')
    ordering = ('-id',)
    readonly_fields = ('created_at', 'updated_at')
