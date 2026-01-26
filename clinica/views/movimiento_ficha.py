# views.py

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView

from clinica.forms.movimiento_ficha import (
    FormSalidaFicha, FiltroSalidaFichaForm, FormEntradaFicha, FormTraspasoFicha
)
from clinica.models import MovimientoFicha
from core.mixin import DataTableMixin
from personas.models.profesionales import Profesional


class SalidaTablaFichaView(LoginRequiredMixin, DataTableMixin, TemplateView):
    """
    Vista para registro masivo de salidas de fichas con AJAX.
    Muestra el formulario de registro y el de filtro, además de la tabla.
    """
    template_name = 'movimiento_ficha/salida_ficha_update.html'
    model = MovimientoFicha

    datatable_columns = [
        'ID', 'RUT', 'Ficha', 'Nombre completo', 'Servicio Clínico Envío',
        'Servicio Clínico Recibe', 'Usuario Envío', 'Fecha envío', 'Estado envio'
    ]
    datatable_order_fields = [
        'id', None, 'ficha__paciente__rut', 'ficha__numero_ficha_sistema',
        'ficha__paciente__apellido_paterno',
        'servicio_clinico_envio__nombre', 'servicio_clinico_recepcion__nombre',
        'usuario_envio__username', 'fecha_envio', 'estado_envio'
    ]
    datatable_search_fields = [
        'ficha__paciente__rut__icontains',
        'ficha__numero_ficha_sistema__icontains',
        'ficha__paciente__nombre__icontains',
        'ficha__paciente__apellido_paterno__icontains',
        'ficha__paciente__apellido_materno__icontains',
        'servicio_clinico_envio__nombre__icontains',
        'servicio_clinico_recepcion__nombre__icontains',
        'usuario_envio__username__icontains',
    ]

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        establecimiento = getattr(self.request.user, 'establecimiento', None)

        context.update({
            'title': 'Registro Masivo de Salida de Fichas',
            'form': FormSalidaFicha(user=self.request.user),
            'filter_form': FiltroSalidaFichaForm(self.request.GET or None),
            'datatable_enabled': True,
            'datatable_order': [[0, 'desc']],
            'columns': self.datatable_columns,
            'list_url': reverse_lazy('salida_ficha_masiva'),
        })

        if establecimiento:
            if 'profesional' in context['filter_form'].fields:
                context['filter_form'].fields['profesional'].queryset = Profesional.objects.filter(
                    establecimiento=establecimiento)
            if 'servicio_clinico' in context['filter_form'].fields:
                from establecimientos.models.servicio_clinico import ServicioClinico
                context['filter_form'].fields['servicio_clinico'].queryset = ServicioClinico.objects.filter(
                    establecimiento=establecimiento)

        return context

    def get_base_queryset(self):
        establecimiento = getattr(self.request.user, 'establecimiento', None)
        qs = MovimientoFicha.objects.filter(
            ficha__establecimiento=establecimiento
        ).select_related(
            'ficha__paciente',
            'servicio_clinico_envio',
            'servicio_clinico_recepcion',
            'usuario_envio'
        )

        # Filtros desde filter_form
        inicio = self.request.GET.get('hora_inicio')
        termino = self.request.GET.get('hora_termino')
        servicio_id = self.request.GET.get('servicio_clinico')
        profesional_id = self.request.GET.get('profesional')

        if inicio:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(inicio)
                qs = qs.filter(fecha_envio__gte=dt)
            except Exception:
                pass
        if termino:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(termino)
                qs = qs.filter(fecha_envio__lte=dt)
            except Exception:
                pass
        if servicio_id:
            qs = qs.filter(servicio_clinico_envio_id=servicio_id)
        if profesional_id:
            qs = qs.filter(usuario_envio_id=profesional_id)

        return qs

    def render_row(self, obj):
        pac = obj.ficha.paciente if obj.ficha else None
        nombre = f"{getattr(pac, 'nombre', '')} {getattr(pac, 'apellido_paterno', '')} {getattr(pac, 'apellido_materno', '')}" if pac else ''
        return {
            'ID': obj.id,
            'RUT': getattr(pac, 'rut', '') if pac else '',
            'Ficha': getattr(obj.ficha, 'numero_ficha_sistema', '') if obj.ficha else '',
            'Nombre completo': nombre.strip(),
            'Servicio Clínico Envío': getattr(obj.servicio_clinico_envio, 'nombre', ''),
            'Servicio Clínico Recibe': getattr(obj.servicio_clinico_recepcion, 'nombre', ''),
            'Usuario Envío': getattr(obj.usuario_envio, 'username', '') if obj.usuario_envio else '',
            'Fecha envío': obj.fecha_envio.strftime('%Y-%m-%d %H:%M') if obj.fecha_envio else '',
            'Estado envio': obj.estado_envio or '',
        }

    def post(self, request, *args, **kwargs):
        """Manejar el POST para crear el movimiento vía AJAX"""
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            try:
                # Intentar leer desde request.body si es JSON puro o desde request.POST
                if request.content_type == 'application/json':
                    data = json.loads(request.body)
                else:
                    data = request.POST

                ficha_id = data.get('ficha_id') or data.get('ficha') or data.get('ficha_id_hidden')

                # Validación si ya existe movimiento en tránsito
                movimiento_abierto = MovimientoFicha.objects.filter(
                    ficha_id=ficha_id,
                    estado_recepcion='EN ESPERA',
                    establecimiento=request.user.establecimiento
                ).exists()

                if movimiento_abierto:
                    return JsonResponse({
                        'success': False,
                        'error': 'La ficha se encuentra actualmente en tránsito.'
                    }, status=400)

                # Crear movimiento
                form = FormSalidaFicha(data, user=request.user)
                if form.is_valid():
                    movimiento = form.save(commit=False)

                    movimiento.usuario_envio = request.user
                    movimiento.establecimiento = request.user.establecimiento
                    movimiento.estado_envio = 'ENVIADO'
                    movimiento.estado_recepcion = 'EN ESPERA'

                    try:
                        movimiento.save()
                        return JsonResponse({
                            'success': True,
                            'message': 'Salida registrada exitosamente',
                            'movimiento_id': movimiento.id
                        })
                    except ValidationError as ve:
                        # Capturar errores de full_clean()
                        errors = ve.message_dict if hasattr(ve, 'message_dict') else str(ve)
                        return JsonResponse({'success': False, 'error': errors}, status=400)
                else:
                    # Formatear errores del formulario para que sean legibles en el frontend
                    error_msg = ""
                    for field, errors in form.errors.items():
                        for error in errors:
                            error_msg += f"{error['message']} " if isinstance(error, dict) else f"{error} "

                    return JsonResponse({'success': False, 'error': error_msg.strip()}, status=400)

            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=500)

        # Si no es AJAX, comportamiento estándar (aunque la descripción pide que no recargue)
        form = FormSalidaFicha(request.POST, user=request.user)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.usuario_envio = request.user
            movimiento.establecimiento = request.user.establecimiento
            movimiento.save()
            return redirect('salida_ficha_masiva')

        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class FichasEnTransito(LoginRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'movimiento_ficha/tabla_salida_ficha_update.html'
    model = MovimientoFicha

    datatable_columns = [
        'ID', 'RUT', 'Ficha', 'Nombre completo', 'Servicio Clínico Envío',
        'Usuario Envío', 'Observación envío', 'Fecha envío', 'Estado envio'
    ]
    datatable_order_fields = [
        'id', None, 'ficha__paciente__rut', 'ficha__numero_ficha_sistema',
        'ficha__paciente__apellido_paterno',
        'servicio_clinico_envio__nombre', 'usuario_envio__username',
        'observacion_envio', 'fecha_envio', 'estado_envio'
    ]
    datatable_search_fields = [
        'ficha__paciente__rut__icontains',
        'ficha__numero_ficha_sistema__icontains',
        'ficha__paciente__nombre__icontains',
        'ficha__paciente__apellido_paterno__icontains',
        'ficha__paciente__apellido_materno__icontains',
        'servicio_clinico_envio__nombre__icontains',
        'usuario_envio__username__icontains',
        'observacion_envio__icontains',
    ]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # ✅ Inyectamos el usuario logueado al form
        return kwargs

    def get(self, request, *args, **kwargs):
        # Si es llamada AJAX para DataTable
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        establecimiento = getattr(self.request.user, 'establecimiento', None)

        # Formulario de filtro
        filter_form = FiltroSalidaFichaForm(self.request.GET or None)
        if establecimiento and 'profesional' in filter_form.fields:
            filter_form.fields['profesional'].queryset = Profesional.objects.filter(establecimiento=establecimiento)

        context.update({
            'title': 'Fichas en Tránsito',
            'filter_form': filter_form,
            'list_url': reverse_lazy('fichas_en_transito'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'desc']],
            'columns': self.datatable_columns,
        })
        return context

    def get_base_queryset(self):
        establecimiento = getattr(self.request.user, 'establecimiento', None)
        qs = (MovimientoFicha.objects.filter(
            estado_envio='ENVIADO',
            estado_traspaso='SIN TRASPASO',
            ficha__establecimiento=establecimiento,
            estado_recepcion='EN ESPERA',
        ).select_related(
            'ficha__paciente',
            'servicio_clinico_envio',
            'usuario_envio'
        ))

        # Filtros desde filter_form
        inicio = self.request.GET.get('hora_inicio')
        termino = self.request.GET.get('hora_termino')
        servicio_id = self.request.GET.get('servicio_clinico')
        profesional_id = self.request.GET.get('profesional')

        if inicio:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(inicio)
                qs = qs.filter(fecha_envio__gte=dt)
            except Exception:
                pass
        if termino:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(termino)
                qs = qs.filter(fecha_envio__lte=dt)
            except Exception:
                pass
        if servicio_id:
            qs = qs.filter(servicio_clinico_envio_id=servicio_id)
        if profesional_id:
            qs = qs.filter(usuario_envio_id=profesional_id)

        return qs

    def render_row(self, obj):
        pac = obj.ficha.paciente if obj.ficha else None
        nombre = f"{getattr(pac, 'nombre', '')} {getattr(pac, 'apellido_paterno', '')} {getattr(pac, 'apellido_materno', '')}" if pac else ''
        return {
            'ID': obj.id,
            'RUT': getattr(pac, 'rut', '') if pac else '',
            'Ficha': getattr(obj.ficha, 'numero_ficha_sistema', '') if obj.ficha else '',
            'Nombre completo': nombre.strip(),
            'Servicio Clínico Envío': getattr(obj.servicio_clinico_envio, 'nombre', ''),
            'Usuario Envío': getattr(obj.usuario_envio, 'username', '') if obj.usuario_envio else '',
            'Observación envío': obj.observacion_envio or '',
            'Fecha envío': obj.fecha_envio.strftime('%Y-%m-%d %H:%M') if obj.fecha_envio else '',
            'Estado envio': obj.estado_envio or '',
        }


class RecepcionTablaFichaView(LoginRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'movimiento_ficha/recepcion_ficha.html'
    model = MovimientoFicha

    datatable_columns = ['ID', 'RUT', 'Ficha', 'Nombre completo', 'Servicio Clínico', 'Profesional', 'Fecha de salida',
                         'Estado']
    datatable_order_fields = ['id', None, 'ficha__paciente__rut', 'ficha__numero_ficha_sistema',
                              'ficha__paciente__apellido_paterno',
                              'servicio_clinico_envio__nombre', 'usuario_envio__username', 'fecha_envio',
                              'estado_recepcion']
    datatable_search_fields = [
        'ficha__paciente__rut__icontains',
        'ficha__numero_ficha_sistema__icontains',
        'ficha__paciente__nombre__icontains',
        'ficha__paciente__apellido_paterno__icontains',
        'ficha__paciente__apellido_materno__icontains',
        'servicio_clinico_envio__nombre__icontains',
        'usuario_envio__username__icontains',
    ]

    def get(self, request, *args, **kwargs):
        # Soporte para AJAX DataTable
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        establecimiento = getattr(self.request.user, 'establecimiento', None)

        # Formulario de entrada
        if 'form' not in context:
            context['form'] = FormEntradaFicha(user=self.request.user)

        # Formulario de filtro (mismo que en salida)
        filter_form = FiltroSalidaFichaForm(self.request.GET or None)
        if establecimiento and 'profesional' in filter_form.fields:
            filter_form.fields['profesional'].queryset = Profesional.objects.filter(establecimiento=establecimiento)

        context.update({
            'title': 'Recepción de Fichas',
            'list_url': reverse_lazy('kardex:recepcion_ficha'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'desc']],
            'columns': self.datatable_columns,
            'filter_form': filter_form,
        })
        return context

    def get_base_queryset(self):
        establecimiento = getattr(self.request.user, 'establecimiento', None)
        qs = MovimientoFicha.objects.filter(
            estado_recepcion__in=['EN ESPERA', 'RECIBIDO'],
            ficha__establecimiento=establecimiento
        ).select_related(
            'ficha__paciente',
            'servicio_clinico_envio',
            'usuario_envio'
        )

        # Filtros desde filter_form (análogos a salida, pero por recepción)
        inicio = self.request.GET.get('hora_inicio')
        termino = self.request.GET.get('hora_termino')
        servicio_id = self.request.GET.get('servicio_clinico')
        profesional_id = self.request.GET.get('profesional')

        if inicio:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(inicio)
                qs = qs.filter(fecha_recepcion__gte=dt)
            except Exception:
                pass
        if termino:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(termino)
                qs = qs.filter(fecha_recepcion__lte=dt)
            except Exception:
                pass
        if servicio_id:
            qs = qs.filter(servicio_clinico_recepcion_id=servicio_id)
        if profesional_id:
            qs = qs.filter(usuario_recepcion_id=profesional_id)

        return qs

    def render_row(self, obj):
        pac = obj.ficha.paciente if obj.ficha else None
        nombre = f"{getattr(pac, 'nombre', '')} {getattr(pac, 'apellido_paterno', '')} {getattr(pac, 'apellido_materno', '')}" if pac else ''
        return {
            'ID': obj.id,
            'RUT': getattr(pac, 'rut', '') if pac else '',
            'Ficha': getattr(obj.ficha, 'numero_ficha_sistema', '') if obj.ficha else '',
            'Nombre completo': nombre.strip(),
            'Servicio Clínico': getattr(obj.servicio_clinico_envio, 'nombre', ''),
            'Profesional': getattr(obj.usuario_envio, 'username', ''),
            'Fecha de salida': obj.fecha_envio.strftime('%Y-%m-%d %H:%M') if obj.fecha_envio else '',
            'Estado': obj.estado_recepcion,
        }

    def post(self, request, *args, **kwargs):
        """Manejar el POST para registrar la recepción vía AJAX"""
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            try:
                if request.content_type == 'application/json':
                    data = json.loads(request.body)
                else:
                    data = request.POST

                movimiento_id = data.get('movimiento_id')
                if not movimiento_id:
                    return JsonResponse({'success': False, 'error': 'No se especificó el movimiento a recibir.'},
                                        status=400)

                try:
                    movimiento = MovimientoFicha.objects.get(
                        pk=movimiento_id,
                        establecimiento=request.user.establecimiento,
                        estado_recepcion='EN ESPERA'
                    )
                except MovimientoFicha.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Movimiento no encontrado o ya procesado.'},
                                        status=404)

                form = FormEntradaFicha(data, instance=movimiento, user=request.user)
                if form.is_valid():
                    movimiento = form.save(commit=False)
                    movimiento.estado_recepcion = 'RECIBIDO'
                    movimiento.usuario_recepcion = request.user
                    movimiento.save()
                    return JsonResponse({
                        'success': True,
                        'message': 'Recepción registrada exitosamente',
                        'movimiento_id': movimiento.id
                    })
                else:
                    error_msg = ""
                    for field, errors in form.errors.items():
                        for error in errors:
                            error_msg += f"{error['message']} " if isinstance(error, dict) else f"{error} "
                    return JsonResponse({'success': False, 'error': error_msg.strip()}, status=400)

            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=500)

        # Comportamiento estándar para POST no-AJAX
        form = FormEntradaFicha(request.POST, user=request.user)
        if form.is_valid():
            # Nota: El form original no maneja el movimiento_id para actualización en modo no-AJAX fácilmente
            # pero mantendremos la lógica básica por compatibilidad si fuera necesario.
            movimiento = form.save(commit=False)
            movimiento.estado_recepcion = 'RECIBIDO'
            movimiento.usuario_recepcion = request.user
            movimiento.save()
            return redirect('entrada_tabla_ficha')

        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class TraspasoTablaFichaView(LoginRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'movimiento_ficha/traspaso_ficha.html'
    model = MovimientoFicha

    datatable_columns = ['ID', 'RUT', 'Ficha', 'Nombre completo', 'Servicio Clínico Envío',
                         'Servicio Clínico Recepción',
                         'Servicio Clínico Traspaso', 'Fecha Traspaso', 'Estado']
    datatable_order_fields = ['id', None, 'ficha__paciente__rut', 'ficha__numero_ficha_sistema',
                              'ficha__paciente__apellido_paterno',
                              'servicio_clinico_envio__nombre', 'servicio_clinico_recepcion__nombre',
                              'servicio_clinico_traspaso__nombre', 'fecha_traspaso', 'estado_traspaso']
    datatable_search_fields = [
        'ficha__paciente__rut__icontains',
        'ficha__numero_ficha_sistema__icontains',
        'ficha__paciente__nombre__icontains',
        'ficha__paciente__apellido_paterno__icontains',
        'ficha__paciente__apellido_materno__icontains',
        'servicio_clinico_envio__nombre__icontains',
        'servicio_clinico_recepcion__nombre__icontains',
        'servicio_clinico_traspaso__nombre__icontains',
    ]

    def get(self, request, *args, **kwargs):
        # Soporte para AJAX DataTable
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        establecimiento = getattr(self.request.user, 'establecimiento', None)

        if 'form' not in context:
            context['form'] = FormTraspasoFicha(user=self.request.user)

        filter_form = FiltroSalidaFichaForm(self.request.GET or None)
        if establecimiento and 'profesional' in filter_form.fields:
            filter_form.fields['profesional'].queryset = Profesional.objects.filter(establecimiento=establecimiento)

        context.update({
            'title': 'Traspaso de Fichas',
            'list_url': reverse_lazy('traspaso_ficha'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'desc']],
            'columns': self.datatable_columns,
            'filter_form': filter_form,
        })
        return context

    def get_base_queryset(self):
        establecimiento = getattr(self.request.user, 'establecimiento', None)
        qs = MovimientoFicha.objects.filter(
            ficha__establecimiento=establecimiento
        ).select_related(
            'ficha__paciente',
            'servicio_clinico_envio',
            'servicio_clinico_recepcion',
            'servicio_clinico_traspaso',
            'usuario_traspaso'
        )

        inicio = self.request.GET.get('hora_inicio')
        termino = self.request.GET.get('hora_termino')
        servicio_id = self.request.GET.get('servicio_clinico')
        profesional_id = self.request.GET.get('profesional')

        if inicio:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(inicio)
                qs = qs.filter(fecha_traspaso__gte=dt)
            except Exception:
                pass
        if termino:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(termino)
                qs = qs.filter(fecha_traspaso__lte=dt)
            except Exception:
                pass
        if servicio_id:
            qs = qs.filter(servicio_clinico_traspaso_id=servicio_id)
        if profesional_id:
            qs = qs.filter(usuario_traspaso_id=profesional_id)

        return qs

    def render_row(self, obj):
        pac = obj.ficha.paciente if obj.ficha else None
        nombre = f"{getattr(pac, 'nombre', '')} {getattr(pac, 'apellido_paterno', '')} {getattr(pac, 'apellido_materno', '')}" if pac else ''

        # Generar HTML para acciones
        actions_html = f'''
            <div class="btn-group">
                <button type="button" class="btn btn-default btn-sm dropdown-toggle" data-toggle="dropdown">
                    <i class="fas fa-cog"></i>
                </button>
                <div class="dropdown-menu">
                    <a class="dropdown-item" href="/clinica/pdfs/ficha/{obj.id}/" target="_blank">
                        <i class="fas fa-file-pdf mr-1 text-danger"></i> Ver PDF
                    </a>
                    <a class="dropdown-item btn-edit" href="#" data-id="{obj.id}" data-rut="{getattr(pac, 'rut', '')}">
                        <i class="fas fa-edit mr-1 text-primary"></i> Editar/Completar
                    </a>
                </div>
            </div>
        '''

        # Generar HTML para Estado (Badge)
        estado = obj.estado_traspaso
        badge_class = 'badge-success' if estado == 'TRASPASADO' else 'badge-secondary'
        estado_html = f'<span class="badge {badge_class}">{estado}</span>'

        return {
            'ID': obj.id,
            'actions': actions_html,
            'RUT': getattr(pac, 'rut', '') if pac else '',
            'Ficha': getattr(obj.ficha, 'numero_ficha_sistema', '') if obj.ficha else '',
            'Nombre completo': nombre.strip(),
            'Servicio Clínico Envío': getattr(obj.servicio_clinico_envio, 'nombre', ''),
            'Servicio Clínico Recepción': getattr(obj.servicio_clinico_recepcion, 'nombre', ''),
            'Servicio Clínico Traspaso': getattr(obj.servicio_clinico_traspaso, 'nombre', ''),
            'Fecha Traspaso': obj.fecha_traspaso.strftime('%Y-%m-%d %H:%M') if obj.fecha_traspaso else '',
            'Estado': estado_html,
        }

    def post(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            try:
                if request.content_type == 'application/json':
                    data = json.loads(request.body)
                else:
                    data = request.POST

                movimiento_id = data.get('movimiento_id')
                if not movimiento_id:
                    return JsonResponse({'success': False, 'error': 'No se especificó el movimiento a traspasar.'},
                                        status=400)

                try:
                    movimiento = MovimientoFicha.objects.get(
                        pk=movimiento_id,
                        establecimiento=request.user.establecimiento
                    )
                except MovimientoFicha.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Movimiento no encontrado.'}, status=404)

                form = FormTraspasoFicha(data, instance=movimiento, user=request.user)
                if form.is_valid():
                    movimiento = form.save(commit=False)
                    movimiento.estado_traspaso = 'TRASPASADO'
                    movimiento.usuario_traspaso = request.user
                    movimiento.save()
                    return JsonResponse({
                        'success': True,
                        'message': 'Traspaso registrado exitosamente',
                        'movimiento_id': movimiento.id
                    })
                else:
                    error_msg = ""
                    for field, errors in form.errors.items():
                        for error in errors:
                            error_msg += f"{error['message']} " if isinstance(error, dict) else f"{error} "
                    return JsonResponse({'success': False, 'error': error_msg.strip()}, status=400)

            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=500)

        return super().get(request, *args, **kwargs)
