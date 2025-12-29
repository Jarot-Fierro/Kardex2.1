from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.views.generic import CreateView, UpdateView, DetailView, FormView
from django.views.generic import TemplateView

from core.history import GenericHistoryListView
from kardex.forms.movimiento_ficha import FormEntradaFicha, FiltroSalidaFichaForm, MovimientoFichaForm
from kardex.forms.movimiento_ficha import FormSalidaFicha
from kardex.forms.movimiento_ficha import FormTraspasoFicha
from kardex.mixin import DataTableMixin
from kardex.models import MovimientoFicha, Ficha
from kardex.models import Profesional


class RecepcionFichaView(LoginRequiredMixin, PermissionRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'kardex/movimiento_ficha/recepcion_ficha.html'
    model = MovimientoFicha

    permission_required = 'kardex.add_movimientoficha'
    raise_exception = True

    datatable_columns = ['ID', 'RUT', 'Ficha', 'Nombre completo', 'Servicio Clínico', 'Profesional', 'Fecha de salida',
                         'Estado']
    datatable_order_fields = ['id', None, 'ficha__paciente__rut', 'ficha__numero_ficha_sistema',
                              'ficha__paciente__apellido_paterno',
                              'servicio_clinico_envio__nombre', 'profesional_envio__username', 'fecha_envio',
                              'estado_recepcion']
    datatable_search_fields = [
        'ficha__paciente__rut__icontains',
        'ficha__numero_ficha_sistema__icontains',
        'ficha__paciente__nombre__icontains',
        'ficha__paciente__apellido_paterno__icontains',
        'ficha__paciente__apellido_materno__icontains',
        'servicio_clinico_envio__nombre__icontains',
        'profesional_envio__nombres__icontains',
    ]

    def get(self, request, *args, **kwargs):
        # Soporte para AJAX DataTable
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = FormEntradaFicha(request.POST, request=request)
        if form.is_valid():
            # La recepción debe ACTUALIZAR el último movimiento de la ficha seleccionada
            ficha = form.cleaned_data.get('ficha')
            profesional_recepcion = form.cleaned_data.get('profesional_recepcion')
            servicio_clinico_recepcion = form.cleaned_data.get('servicio_clinico_recepcion')
            observacion_recepcion = form.cleaned_data.get('observacion_recepcion')
            fecha_recepcion = form.cleaned_data.get('fecha_recepcion')

            user = request.user
            ficha_instance = Ficha.objects.filter(numero_ficha_sistema=ficha.numero_ficha_sistema,
                                                  establecimiento=user.establecimiento).first()

            try:
                mov = MovimientoFicha.objects.filter(
                    ficha=ficha_instance
                ).order_by('-fecha_envio').first()
            except Exception:
                mov = None

            if not mov:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse(
                        {'ok': False, 'errors': {'ficha': ['No existe un envío previo para esta ficha.']}}, status=400)
                messages.error(request, 'No existe un envío previo para esta ficha.')
                context = self.get_context_data(form=form)
                return self.render_to_response(context)

            # Completar recepción sobre el movimiento encontrado
            # Si ya estaba recepcionado, no permitir re-modificar
            if mov.estado_recepcion == 'RECIBIDO':
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'ok': False, 'errors': {'__all__': ['El movimiento ya fue recepcionado.']}},
                                        status=400)
                messages.error(request, 'El movimiento ya fue recepcionado.')
                context = self.get_context_data(form=form)
                return self.render_to_response(context)

            mov.usuario_recepcion = request.user
            mov.profesional_recepcion = profesional_recepcion
            # Asignar instancia real de ServicioClinico desde el usuario (el campo del form es solo display)
            mov.servicio_clinico_recepcion = getattr(request.user, 'servicio_clinico', None)
            mov.observacion_recepcion = observacion_recepcion
            mov.fecha_recepcion = fecha_recepcion or now()
            # Marcar recepción como RECIBIDO explícitamente
            mov.estado_recepcion = 'RECIBIDO'
            mov.save()

            messages.success(request, 'Recepción registrada correctamente.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': True, 'id': mov.id})
            return self.get(request, *args, **kwargs)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
            messages.error(request, 'El formulario contiene errores. Por favor, verifique los campos.')
            context = self.get_context_data(form=form)
            return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = kwargs.get('form') or FormEntradaFicha(request=self.request)
        establecimiento = getattr(self.request.user, 'establecimiento', None)
        if establecimiento and 'profesional_recepcion' in form.fields:
            form.fields['profesional_recepcion'].queryset = Profesional.objects.filter(establecimiento=establecimiento)

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
            'form': form,
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
            'profesional_envio'
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
            'Profesional': getattr(obj.profesional_envio, 'nombres', ''),
            'Fecha de salida': obj.fecha_envio.strftime('%Y-%m-%d %H:%M') if obj.fecha_envio else '',
            'Estado': obj.estado_recepcion,
        }


class SalidaFichaView(LoginRequiredMixin, PermissionRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'kardex/movimiento_ficha/salida_ficha.html'
    model = MovimientoFicha
    permission_required = 'kardex.view_movimientoficha'
    raise_exception = True

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

    def post(self, request, *args, **kwargs):
        form = FormSalidaFicha(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.usuario_envio = request.user
            if getattr(obj, 'fecha_envio', None) is None:
                from django.utils.timezone import now as djnow
                obj.fecha_envio = djnow()
            # estados se mantienen por defecto en el modelo
            obj.save()
            messages.success(request, 'Salida registrada correctamente.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': True, 'id': obj.id})
            return self.get(request, *args, **kwargs)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
            messages.error(request, 'El formulario contiene errores.')
            context = self.get_context_data(form=form)
            return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        establecimiento = getattr(self.request.user, 'establecimiento', None)

        # Formulario principal
        form = kwargs.get('form') or FormSalidaFicha(user=self.request.user)
        if establecimiento and 'profesional_envio' in form.fields:
            form.fields['profesional_envio'].queryset = Profesional.objects.filter(establecimiento=establecimiento)

        # Formulario de filtro
        filter_form = FiltroSalidaFichaForm(self.request.GET or None)
        if establecimiento and 'profesional' in filter_form.fields:
            filter_form.fields['profesional'].queryset = Profesional.objects.filter(establecimiento=establecimiento)

        context.update({
            'title': 'Salida de Fichas',
            'form': form,
            'filter_form': filter_form,
            'list_url': reverse_lazy('kardex:salida_ficha'),
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


MODULE_NAME = 'Movimientos de Ficha'


class TraspasoFichaView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'kardex/movimiento_ficha/traspaso_ficha.html'
    model = MovimientoFicha
    permission_required = 'kardex.add_movimientoficha'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        form = FormTraspasoFicha(request.POST, request=request, user=request.user)
        if form.is_valid():
            ficha = form.cleaned_data.get('ficha')
            profesional_traspaso = form.cleaned_data.get('profesional_traspaso')
            servicio_clinico_traspaso = form.cleaned_data.get('servicio_clinico_traspaso')
            fecha_traspaso = form.cleaned_data.get('fecha_traspaso')

            try:
                mov = MovimientoFicha.objects.filter(
                    ficha=ficha,
                    fecha_envio__isnull=False
                ).order_by('-updated_at').first()
            except Exception:
                mov = None

            if not mov:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse(
                        {'ok': False, 'errors': {'ficha': ['No existe un envío previo para esta ficha.']}}, status=400)
                messages.error(request, 'No existe un envío previo para esta ficha.')
                context = self.get_context_data(form=form)
                return self.render_to_response(context)

            # Registrar traspaso
            mov.usuario_traspaso = request.user
            mov.profesional_traspaso = profesional_traspaso
            mov.servicio_clinico_traspaso = servicio_clinico_traspaso
            mov.fecha_traspaso = fecha_traspaso or now()
            # Cambiar estado de traspaso a TRASPASDO (según choices) al registrar traspaso
            mov.estado_traspaso = 'TRASPASDO'
            mov.save()

            messages.success(request, 'Traspaso registrado correctamente.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': True, 'id': mov.id})
            return self.get(request, *args, **kwargs)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
            messages.error(request, 'El formulario contiene errores. Por favor, verifique los campos.')
            context = self.get_context_data(form=form)
            return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = kwargs.get('form') or FormTraspasoFicha(request=self.request, user=self.request.user)
        establecimiento = getattr(self.request.user, 'establecimiento', None)
        if establecimiento and 'profesional_traspaso' in form.fields:
            form.fields['profesional_traspaso'].queryset = Profesional.objects.filter(establecimiento=establecimiento)

        context.update({
            'title': 'Traspaso de Fichas',
            'list_url': reverse_lazy('kardex:traspaso_ficha'),
            'form': form,
        })
        return context


class MovimientoFichaListView(PermissionRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'kardex/movimiento_ficha/list.html'
    model = MovimientoFicha
    datatable_columns = [
        'ID',
        'RUT',
        'Ficha',
        'Nombre completo',
        'Servicio Clínico Envío',
        'Servicio Clínico Recepción',
        'Profesional Envío',
        'Observación Envío',
        'Fecha/hora Envío',
        'Estado Envío',
    ]

    datatable_order_fields = ['id', None, 'ficha__numero_ficha_sistema', 'servicio_clinico_envio__nombre',
                              'estado_envio',
                              'fecha_envio']
    datatable_search_fields = [
        'ficha__numero_ficha_sistema__icontains', 'servicio_clinico_envio__nombre__icontains', 'estado_envio__icontains'
    ]

    permission_required = 'kardex.view_movimiento_ficha'
    raise_exception = True

    permission_view = 'kardex.view_movimiento_ficha'
    permission_update = 'kardex.change_movimiento_ficha'

    url_detail = 'kardex:movimiento_ficha_detail'
    url_update = 'kardex:movimiento_ficha_update'

    def render_row(self, obj):
        pac = obj.ficha.paciente if obj.ficha else None
        nombre = f"{getattr(pac, 'nombre', '')} {getattr(pac, 'apellido_paterno', '')} {getattr(pac, 'apellido_materno', '')}" if pac else ''
        return {
            'ID': obj.id,
            'RUT': getattr(pac, 'rut', '') if pac else '',
            'Ficha': getattr(obj.ficha, 'numero_ficha_sistema', '') if obj.ficha else '',
            'Nombre completo': nombre.strip(),
            'Servicio Clínico Envío': getattr(obj.servicio_clinico_envio, 'nombre', ''),
            'Servicio Clínico Recepción': getattr(obj.servicio_clinico_recepcion, 'nombre', ''),
            'Profesional Envío': getattr(obj.profesional_envio, 'nombres', '') if obj.profesional_envio else '',
            'Observación Envío': obj.observacion_envio or '',
            'Fecha/hora Envío': obj.fecha_envio.strftime('%Y-%m-%d %H:%M') if obj.fecha_envio else '',
            'Estado Envío': obj.estado_envio,
        }

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Movimientos de Ficha',
            'list_url': reverse_lazy('kardex:movimiento_ficha_list'),
            'create_url': reverse_lazy('kardex:movimiento_ficha_create'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'desc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context


class MovimientoFichaDetailView(PermissionRequiredMixin, DetailView):
    model = MovimientoFicha
    template_name = 'kardex/movimiento_ficha/detail.html'

    permission_required = 'kardex.view_movimiento_ficha'
    raise_exception = True

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class MovimientoFichaCreateView(PermissionRequiredMixin, CreateView):
    template_name = 'kardex/movimiento_ficha/form.html'
    model = MovimientoFicha
    form_class = MovimientoFichaForm  # ← ESTE era el error
    success_url = reverse_lazy('kardex:movimiento_ficha_list')

    permission_required = 'kardex.add_movimientoficha'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo Movimiento de Ficha'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class MovimientoFichaUpdateView(UpdateView, FormView):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    template_name = 'kardex/movimiento_ficha/form_update.html'
    model = MovimientoFicha
    form_class = MovimientoFichaForm
    success_url = reverse_lazy('kardex:movimiento_ficha_list')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.estado_recepcion == 'RECIBIDO':
            messages.error(request, 'Este movimiento ya fue recepcionado.')
            return redirect(self.success_url)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'title': 'Editar Movimiento de Ficha',
            'list_url': self.success_url,
            'action': 'edit',
            'module_name': MODULE_NAME,
        })

        return context

    def form_valid(self, form):
        obj = form.save(commit=False)
        user = self.request.user
        # Usuario que recepciona
        if hasattr(obj, 'usuario_recepcion'):
            obj.usuario_recepcion = user
        # Servicio clínico de recepción desde el usuario, si existe
        if hasattr(user, 'servicio_clinico') and user.servicio_clinico:
            obj.servicio_clinico_recepcion = user.servicio_clinico
        # Fecha de recepción si no viene desde el formulario
        if not getattr(obj, 'fecha_recepcion', None):
            obj.fecha_recepcion = now()
        # Estado de recepción pasa a RECIBIDO
        obj.estado_recepcion = 'RECIBIDO'
        obj.save()
        messages.success(self.request, 'Movimiento actualizado y recepcionado correctamente.')
        return redirect(self.success_url)


class MovimientoFichaTransitoListView(PermissionRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'kardex/movimiento_ficha/list.html'
    model = MovimientoFicha

    # Usamos las mismas columnas que en la vista de Salida para mantener consistencia visual
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

    permission_required = 'kardex.view_movimientoficha'
    raise_exception = True

    permission_view = 'kardex.view_movimientoficha'
    permission_update = 'kardex.change_movimientoficha'

    url_detail = 'kardex:movimiento_ficha_detail'
    url_update = 'kardex:movimiento_ficha_update'

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

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Fichas en tránsito',
            'list_url': reverse_lazy('kardex:movimiento_ficha_transito'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'asc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context

    def get_base_queryset(self):
        # En tránsito: ENVIADO y no recepcionado aún, o TRASPASDO
        from django.db.models import Q
        qs = MovimientoFicha.objects.select_related(
            'ficha__paciente', 'servicio_clinico_envio', 'usuario_envio'
        ).filter(
            Q(estado_envio='ENVIADO') & ~Q(estado_recepcion='RECIBIDO') | Q(estado_traspaso='TRASPASDO')
        )
        return qs


class MovimientosFichasHistoryListView(GenericHistoryListView):
    base_model = MovimientoFicha
    permission_required = 'kardex.view_movimiento_ficha'
    template_name = 'kardex/history/list.html'
