from django.contrib import admin

from .models import FusionFicha


@admin.register(FusionFicha)
class FusionFichaAdmin(admin.ModelAdmin):
    list_display = ('paciente_real_id', 'rut_real', 'nombres_real', 'apellidos_real', 'establecimiento', 'created_at')
    list_filter = ('establecimiento', 'created_at')
    search_fields = ('rut_real', 'rut_ficticio', 'nombres_real', 'apellidos_real')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
