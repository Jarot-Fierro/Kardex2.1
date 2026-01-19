# views.py

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView
from django.views.generic.base import TemplateView

from clinica.forms.movimiento_ficha import FormSalidaFicha, FiltroSalidaFichaForm
from clinica.models import MovimientoFicha
from core.mixin import DataTableMixin
from personas.models.profesionales import Profesional


class SalidaFicha2View(LoginRequiredMixin, CreateView):
    """
    Vista para registro masivo de salidas de fichas con AJAX.
    Optimizada para escaneo continuo con lector de códigos de barras.
    """
    model = MovimientoFicha
    form_class = FormSalidaFicha
    template_name = 'movimiento_ficha/salida_ficha_update.html'
    success_url = reverse_lazy('lista_movimientos')

    def get_form_kwargs(self):
        """Pasar el usuario al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Agregar contexto adicional"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Registro Masivo de Salida de Fichas'
        context['subtitle'] = 'Escaneo Continuo con Lector de Códigos de Barras'
        return context

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """Manejar peticiones AJAX"""
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return self.handle_ajax(request)
        return super().dispatch(request, *args, **kwargs)

    def handle_ajax(self, request):
        """Procesar peticiones AJAX para registro rápido"""
        if request.method == 'POST':
            try:
                data = json.loads(request.body)

                # Validar datos requeridos
                required_fields = [
                    'ficha_id',
                    'servicio_envio_id',
                    'servicio_recepcion_id',
                    'profesional_id'
                ]

                for field in required_fields:
                    if field not in data or not data[field]:
                        return JsonResponse({
                            'success': False,
                            'error': f'Campo requerido faltante: {field}'
                        }, status=400)

                ficha_id = data['ficha_id']

                # ------------------------------------------------------------------
                # VALIDACIÓN CRÍTICA:
                # No permitir salida si la ficha ya tiene un movimiento EN TRÁNSITO
                # ------------------------------------------------------------------
                movimiento_abierto = MovimientoFicha.objects.filter(
                    ficha_id=ficha_id,
                    estado_recepcion='EN ESPERA',
                    establecimiento=request.user.establecimiento
                ).exists()

                if movimiento_abierto:
                    return JsonResponse({
                        'success': False,
                        'error': (
                            'La ficha se encuentra actualmente en tránsito y no puede '
                            'ser enviada nuevamente hasta ser recepcionada.'
                        )
                    }, status=400)

                # ------------------------------------------------------------------
                # CREAR MOVIMIENTO DE SALIDA
                # ------------------------------------------------------------------
                movimiento = MovimientoFicha(
                    ficha_id=ficha_id,
                    servicio_clinico_envio_id=data['servicio_envio_id'],
                    servicio_clinico_recepcion_id=data['servicio_recepcion_id'],
                    profesional_envio_id=data['profesional_id'],
                    observacion_envio=data.get('observacion', ''),
                    usuario_envio=request.user,
                    establecimiento=request.user.establecimiento,
                    estado_envio='ENVIADO',
                    estado_recepcion='EN ESPERA'
                )

                movimiento.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Salida registrada exitosamente',
                    'movimiento_id': movimiento.id,
                    'ficha_numero': movimiento.ficha.numero_ficha_sistema if movimiento.ficha else '',
                    'timestamp': movimiento.created_at.strftime('%H:%M:%S')
                })

            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'error': 'Datos JSON inválidos'
                }, status=400)

            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=500)

        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)

    def form_valid(self, form):
        """Manejar envío normal del formulario"""
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Ya manejado por handle_ajax
            return JsonResponse({'success': True})

        response = super().form_valid(form)

        # Si es una petición normal, redirigir
        if self.request.POST.get('continuar_escaneo'):
            # Mantener los valores de los servicios y profesional
            self.request.session['salida_masiva_config'] = {
                'servicio_envio_id': form.cleaned_data['servicio_clinico_envio'].id,
                'servicio_recepcion_id': form.cleaned_data['servicio_clinico_recepcion'].id,
                'profesional_id': form.cleaned_data['profesional_envio'].id,
                'observacion': form.cleaned_data['observacion_envio']
            }

            return redirect('salida_ficha_masiva')

        return response


class SalidaTablaFichaView(LoginRequiredMixin, DataTableMixin, TemplateView):
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
            'title': 'Salida de Fichas',
            'filter_form': filter_form,
            'list_url': reverse_lazy('salida_ficha'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'desc']],
            'columns': self.datatable_columns,
        })
        return context

    def get_base_queryset(self):
        establecimiento = getattr(self.request.user, 'establecimiento', None)
        qs = MovimientoFicha.objects.filter(
            estado_envio='ENVIADO',
            ficha__establecimiento=establecimiento
        ).select_related(
            'ficha__paciente',
            'servicio_clinico_envio',
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
