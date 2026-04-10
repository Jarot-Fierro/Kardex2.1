from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse
from django.http.response import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView
from django.views.generic import UpdateView, DetailView

from clinica.forms.ficha import FichaForm, FormFichaTarjeta
from clinica.models import Ficha
from clinica.models.movimiento_ficha_monologo_controlado import MovimientoMonologoControlado
from core.history import GenericHistoryListView
from core.mixin import DataTableMixin
from respaldos.models.respaldo_ficha import RespaldoFicha
from respaldos.models.respaldo_movimiento import RespaldoMovimientoMonologoControlado

MODULE_NAME = 'Fichas'


class FichaListView(DataTableMixin, TemplateView):
    template_name = 'ficha/list.html'
    model = Ficha
    datatable_columns = ['ID', 'Número', 'N° Tarjeta', 'Establecimiento', 'RUT', 'Código', 'Paciente', 'Fecha Creación']
    datatable_order_fields = ['id', 'numero_ficha_sistema', 'numero_ficha_tarjeta', 'establecimiento__nombre',
                              'paciente__rut', 'paciente__codigo', None, 'created_at']
    datatable_search_fields = [
        'numero_ficha_sistema__icontains',
        'numero_ficha_tarjeta__icontains',
        'usuario__username__icontains',
        'paciente__rut__icontains',
        'paciente__codigo__icontains',
        'paciente__nombre__icontains',
        'establecimiento__nombre__icontains'
    ]

    url_detail = 'ficha_detail'
    export_report_url_name = 'export_ficha'

    def get_url_update(self):
        user = self.request.user
        if getattr(user, 'rol', None) and user.rol.fichas == 2:
            return 'ficha_update'
        return None

    def get_url_delete(self):
        user = self.request.user
        if getattr(user, 'rol', None) and user.rol.fichas == 2:
            return 'ficha_delete'
        return None

    def render_row(self, obj):
        pac = getattr(obj, 'paciente', None)
        est = getattr(obj, 'establecimiento', None)
        nombre_completo = ''
        if pac:
            nombre_completo = f"{(getattr(pac, 'nombre', '') or '').upper()} {(getattr(pac, 'apellido_paterno', '') or '').upper()} {(getattr(pac, 'apellido_materno', '') or '').upper()}".strip()
        return {
            'ID': obj.id,
            'Número': obj.numero_ficha_sistema,
            'N° Tarjeta': obj.numero_ficha_tarjeta,
            'Establecimiento': (getattr(est, 'nombre', '') or '').upper(),
            'RUT': getattr(pac, 'rut', '') if pac else '',
            'Código': getattr(pac, 'codigo', '') if pac else '',
            'Paciente': nombre_completo,
            'Fecha Creación': obj.created_at.strftime('%Y-%m-%d %H:%M') if getattr(obj, 'created_at', None) else '',
        }

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Fichas',
            'list_url': reverse_lazy('ficha_list'),
            'create_url': reverse_lazy('ficha_create'),
            'export_report_url_name': self.export_report_url_name,
            'datatable_enabled': True,
            'datatable_order': [[0, 'desc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
        })
        return context

    def get_base_queryset(self):
        # Optimiza consultas y, si aplica la política del sistema, restringe por establecimiento del usuario
        qs = Ficha.objects.select_related(
            'paciente',
            'establecimiento',
        )
        # Si la app en otras vistas filtra por establecimiento, puede activarse aquí:
        user = getattr(self.request, 'user', None)
        establecimiento = getattr(user, 'establecimiento', None) if user else None
        if establecimiento:
            qs = qs.filter(establecimiento=establecimiento, status=True)
        return qs


class FichaDetailView(DetailView):
    model = Ficha
    template_name = 'ficha/detail.html'
    permission_required = 'view_paciente'

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class FichaUpdateView(UpdateView):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    template_name = 'ficha/form.html'
    model = Ficha
    form_class = FichaForm
    success_url = reverse_lazy('ficha_list')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.save()
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.success(request, 'Ficha actualizada correctamente')
            return redirect(self.success_url)
        from django.contrib import messages
        messages.error(request, 'Hay errores en el formulario')
        return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Ficha'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class TogglePasivadoFichaView(View):

    def get(self, request, pk, *args, **kwargs):
        try:
            ficha = Ficha.objects.get(pk=pk)
        except Ficha.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': False, 'error': 'La ficha indicada no existe.'}, status=404)
            messages.error(request, 'La ficha indicada no existe.')
            return redirect('kardex:paciente_query')

        ficha.pasivado = not bool(ficha.pasivado)
        ficha.save(update_fields=['pasivado'])

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({
                'success': True,
                'ficha_id': ficha.id,
                'pasivado': bool(ficha.pasivado),
                'message': 'La ficha fue pasivada correctamente.' if ficha.pasivado else 'La ficha fue despasivada correctamente.'
            })

        if ficha.pasivado:
            messages.success(request, 'La ficha fue pasivada correctamente.')
        else:
            messages.success(request, 'La ficha fue despasivada correctamente.')
        # Volver a la pantalla de consulta/creación
        return redirect('paciente_query')


class FichaTarjetaView(UpdateView):
    template_name = '/ficha/form_numero_ficha.html'
    model = Ficha
    form_class = FormFichaTarjeta
    success_url = reverse_lazy('ficha_list')

    def get_initial(self):
        """Precargar datos iniciales"""
        initial = super().get_initial()
        initial['establecimiento'] = self.object.establecimiento
        return initial

    def validate_unique_number(self, number, ficha_id, establecimiento_id):
        """
        Valida que el número no exista en el mismo establecimiento
        """
        from django.db.models import Q

        # Verificar si ya existe en el mismo establecimiento
        exists = Ficha.objects.filter(
            establecimiento_id=establecimiento_id
        ).filter(
            Q(numero_ficha_sistema=number) | Q(numero_ficha_tarjeta=number)
        ).exclude(id=ficha_id).exists()

        return exists

    def get_conflicting_ficha(self, number, ficha_id, establecimiento_id):
        """
        Obtiene la ficha que causa conflicto
        """
        from django.db.models import Q

        return Ficha.objects.filter(
            establecimiento_id=establecimiento_id
        ).filter(
            Q(numero_ficha_sistema=number) | Q(numero_ficha_tarjeta=number)
        ).exclude(id=ficha_id).first()

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        # Obtener datos importantes
        numero_ficha_tarjeta = request.POST.get('numero_ficha_tarjeta')
        establecimiento_id = self.object.establecimiento_id

        # Validación personalizada si se proporciona número
        if numero_ficha_tarjeta and numero_ficha_tarjeta.strip():
            try:
                numero = int(numero_ficha_tarjeta.strip())

                # Validaciones básicas
                if numero <= 0:
                    error_msg = 'El número de ficha debe ser mayor a 0.'
                    return self.handle_validation_error(request, 'numero_ficha_tarjeta', error_msg)

                # Validar unicidad en el establecimiento
                if self.validate_unique_number(numero, self.object.id, establecimiento_id):
                    ficha_conflicto = self.get_conflicting_ficha(numero, self.object.id, establecimiento_id)

                    if ficha_conflicto:
                        paciente_conflicto = ficha_conflicto.paciente
                        campo_conflicto = "número de ficha sistema" if ficha_conflicto.numero_ficha_sistema == numero else "número de ficha tarjeta"

                        # Construir nombre completo de forma segura (sin depender de nombre_completo())
                        _nombre_completo = f"{(getattr(paciente_conflicto, 'nombre', '') or '').strip()} {(getattr(paciente_conflicto, 'apellido_paterno', '') or '').strip()} {(getattr(paciente_conflicto, 'apellido_materno', '') or '').strip()}".strip()
                        error_msg = (
                            f'El número {numero} ya está asignado como {campo_conflicto} '
                            f'al paciente: {_nombre_completo} '
                            f'(RUT: {paciente_conflicto.rut}). '
                            f'Por favor, seleccione otro número.'
                        )
                        return self.handle_validation_error(request, 'numero_ficha_tarjeta', error_msg)

            except ValueError:
                error_msg = 'El número de ficha debe ser un valor numérico válido.'
                return self.handle_validation_error(request, 'numero_ficha_tarjeta', error_msg)

        # Si el formulario es válido
        if form.is_valid():
            # Guardar los datos del formulario
            self.object = form.save(commit=False)

            # Si se proporcionó número de ficha tarjeta, sincronizar con sistema
            if numero_ficha_tarjeta and numero_ficha_tarjeta.strip():
                self.object.numero_ficha_sistema = numero_ficha_tarjeta.strip()

            # Guardar cambios
            self.object.save()

            # Manejar respuesta
            return self.handle_success_response(request)

        # Formulario inválido
        return self.handle_form_error(request, form)

    def handle_validation_error(self, request, field, message):
        """Maneja errores de validación"""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': {field: [message]}
            }, status=400)
        messages.error(request, message)
        return self.form_invalid(self.get_form())

    def handle_success_response(self, request):
        """Maneja respuesta exitosa"""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Construir nombre completo de forma segura (sin depender de nombre_completo())
            _pac = getattr(self.object, 'paciente', None)
            _nombre_completo = ''
            if _pac:
                _nombre_completo = f"{(getattr(_pac, 'nombre', '') or '').strip()} {(getattr(_pac, 'apellido_paterno', '') or '').strip()} {(getattr(_pac, 'apellido_materno', '') or '').strip()}".strip()
            return JsonResponse({
                'success': True,
                'ficha_id': self.object.id,
                'paciente_id': self.object.paciente.id,
                'establecimiento_id': self.object.establecimiento_id,
                'numero_ficha_sistema': self.object.numero_ficha_sistema,
                'numero_ficha_tarjeta': self.object.numero_ficha_tarjeta,
                'paciente_nombre': _nombre_completo,
                'paciente_rut': self.object.paciente.rut,
                'establecimiento_nombre': str(self.object.establecimiento),
                'message': f'Ficha actualizada correctamente en {self.object.establecimiento}. '
                           f'Número de ficha: {self.object.numero_ficha_tarjeta}'
            })

        messages.success(
            request,
            f'Ficha actualizada correctamente en {self.object.establecimiento}. '
            f'Número de ficha: {self.object.numero_ficha_tarjeta}'
        )
        return redirect(self.success_url)

    def handle_form_error(self, request, form):
        """Maneja errores del formulario"""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

        messages.error(request, 'Hay errores en el formulario de ficha')
        return self.form_invalid(form)


class PacientePasivadosListView(FichaListView):
    export_report_url_name = 'export_ficha_pasivada'

    def get_base_queryset(self):
        return Ficha.objects.filter(pasivado=True, status=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Fichas Pasivadas',
            'list_url': reverse_lazy('ficha_pasivados_list'),
        })
        return context


class FichaDuplicadaListView(FichaListView):
    def get_base_queryset(self):
        fichas_duplicadas_ids = (
            Ficha.objects
            .filter(status=True)
            .values('numero_ficha_sistema', 'establecimiento')
            .annotate(total=Count('id'))
            .filter(total__gt=1)
            .values('numero_ficha_sistema', 'establecimiento')
        )

        from django.db.models import Q
        query = Q()
        for item in fichas_duplicadas_ids:
            query |= Q(
                numero_ficha_sistema=item['numero_ficha_sistema'],
                establecimiento=item['establecimiento']
            )

        if not query:
            return Ficha.objects.none()

        return (
            Ficha.objects
            .filter(status=True)
            .filter(query)
            .select_related('paciente', 'establecimiento')
            .order_by('establecimiento', 'numero_ficha_sistema', 'id')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Fichas con Número Duplicado por Establecimiento',
            'list_url': reverse_lazy('ficha_list_duplicados'),
        })
        return context


class FichaHistoryListView(GenericHistoryListView):
    base_model = Ficha
    permission_required = 'view_ficha'
    template_name = 'history/list.html'

    url_last_page = 'ficha_list'

    def get_base_queryset(self):
        return self.model.objects.filter(establecimiento_id=self.request.user.establecimiento).select_related(
            'history_user').order_by('-history_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_last_page'] = self.url_last_page
        return context


class FichaDeleteView(View):
    def post(self, request, pk, *args, **kwargs):
        ficha = get_object_or_404(Ficha, pk=pk)
        user = request.user

        # Verificar permisos (permisos totales == 2)
        if not (getattr(user, 'rol', None) and user.rol.fichas == 2):
            messages.error(request, 'No tiene permisos para eliminar fichas.')
            return redirect('ficha_paciente_manage')

        motivo = request.POST.get('motivo_eliminacion', 'Sin motivo especificado')

        try:
            with transaction.atomic():
                # 1. Respaldar Movimientos asociados
                movimientos = MovimientoMonologoControlado.objects.filter(ficha=ficha)
                for mov in movimientos:
                    RespaldoMovimientoMonologoControlado.objects.create(
                        rut=mov.rut,
                        numero_ficha=mov.numero_ficha,
                        fecha_salida=mov.fecha_salida,
                        usuario_entrega=mov.usuario_entrega,
                        usuario_entrega_id=mov.usuario_entrega_id,
                        fecha_entrada=mov.fecha_entrada,
                        usuario_entrada=mov.usuario_entrada,
                        usuario_entrada_id=mov.usuario_entrada_id,
                        fecha_traspaso=mov.fecha_traspaso,
                        usuario_traspaso=mov.usuario_traspaso,
                        observacion_salida=mov.observacion_salida,
                        observacion_entrada=mov.observacion_entrada,
                        observacion_traspaso=mov.observacion_traspaso,
                        profesional=mov.profesional,
                        profesional_anterior=mov.profesional_anterior,
                        rut_paciente=None,
                        establecimiento=mov.establecimiento,
                        ficha=None,  # Se pierde la relación física
                        servicio_clinico_destino=mov.servicio_clinico_destino,
                        estado=mov.estado,
                        usuario_eliminacion=user,
                        motivo_eliminacion=motivo
                    )
                    # El borrado físico de movimientos se dará por el CASCADE si está definido,
                    # o lo hacemos explícito si es PROTECT.
                    # Según el modelo original, ficha es PROTECT en Movimiento.
                    # Pero el usuario dice que se deben borrar de la tabla principal.
                    mov.delete()

                # 2. Respaldar Ficha
                RespaldoFicha.objects.create(
                    numero_ficha_sistema=ficha.numero_ficha_sistema,
                    numero_ficha_tarjeta=ficha.numero_ficha_tarjeta,
                    numero_ficha_respaldo=ficha.numero_ficha_respaldo,
                    rut=ficha.paciente.rut if ficha.paciente else 'SIN RUT',
                    pasivado=ficha.pasivado,
                    observacion=ficha.observacion,
                    usuario=ficha.usuario,
                    usuario_anterior=ficha.usuario_anterior,
                    rut_anterior=ficha.rut_anterior,
                    fecha_creacion_anterior=ficha.fecha_creacion_anterior,
                    paciente=None,
                    fecha_mov=ficha.fecha_mov,
                    establecimiento=ficha.establecimiento,
                    sector=ficha.sector,
                    usuario_eliminacion=user,
                    motivo_eliminacion=motivo
                )

                # 3. Eliminar Ficha
                ficha.delete()

            messages.success(request, 'Ficha y sus movimientos respaldados y eliminados correctamente.')
        except Exception as e:
            messages.error(request, f'Error al eliminar la ficha: {str(e)}')

        return redirect('ficha_paciente_manage')
