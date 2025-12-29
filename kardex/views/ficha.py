from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.http.response import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, UpdateView, DetailView
from django.views.generic import TemplateView

from core.history import GenericHistoryListView
from kardex.forms.fichas import FormFicha, FormFichaTarjeta
from kardex.mixin import DataTableMixin
from kardex.models import Ficha

MODULE_NAME = 'Fichas'


class FichaListView(PermissionRequiredMixin, DataTableMixin, TemplateView):
    template_name = 'kardex/ficha/list.html'
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

    permission_required = 'kardex.view_ficha'
    raise_exception = True

    permission_view = 'kardex.view_ficha'

    url_detail = 'kardex:ficha_detail'
    url_update = 'kardex:ficha_update'
    export_report_url_name = 'reports:export_ficha'

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
            'list_url': reverse_lazy('kardex:ficha_list'),
            'create_url': reverse_lazy('kardex:ficha_create'),
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
            qs = qs.filter(establecimiento=establecimiento)
        return qs


class FichaDetailView(PermissionRequiredMixin, DetailView):
    model = Ficha
    template_name = 'kardex/ficha/detail.html'

    permission_required = 'kardex.view_ficha'
    raise_exception = True

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class FichaCreateView(PermissionRequiredMixin, CreateView):
    """
    Vista para crear o editar fichas:
    - Si no viene ficha_id en POST, crea una ficha nueva.
    - Si viene ficha_id, actualiza la ficha existente.
    """
    template_name = 'kardex/ficha/form.html'
    model = Ficha
    form_class = FormFicha
    success_url = reverse_lazy('kardex:ficha_list')

    permission_required = 'kardex.change_ficha'  # Cambiar si quieres que permita crear
    raise_exception = True

    def post(self, request, *args, **kwargs):
        self.object = None
        ficha_id = (request.POST.get('ficha_id') or '').strip()
        instance = None
        if ficha_id:
            try:
                instance = Ficha.objects.get(pk=ficha_id)
                self.object = instance
            except Ficha.DoesNotExist:
                from django.contrib import messages
                messages.error(request, 'La ficha seleccionada no existe.')
                return self.render_to_response(self.get_context_data(form=self.get_form(), open_modal=True))

        form = self.get_form()
        if instance is not None:
            form.instance = instance  # Edición
        # Si instance es None, form.save() creará una nueva ficha

        if form.is_valid():
            saved_obj = form.save()
            self.object = saved_obj
            from django.contrib import messages
            from django.shortcuts import redirect
            if instance:
                messages.success(request, 'Ficha actualizada correctamente')
            else:
                messages.success(request, 'Ficha creada correctamente')
            return redirect(self.success_url)

        from django.contrib import messages
        messages.error(request, 'Hay errores en el formulario')
        self.object = instance
        return self.render_to_response(self.get_context_data(form=form, open_modal=True))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear / Editar Ficha'
        context['list_url'] = self.success_url
        context['action'] = 'edit' if getattr(self, 'object', None) else 'create'
        context['module_name'] = MODULE_NAME
        if getattr(self, 'object', None) is not None:
            context['ficha'] = self.object
        return context


class FichaUpdateView(PermissionRequiredMixin, UpdateView):
    template_name = 'kardex/ficha/form.html'
    model = Ficha
    form_class = FormFicha
    success_url = reverse_lazy('kardex:ficha_list')
    permission_required = 'kardex.change_ficha'
    raise_exception = True

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


class TogglePasivadoFichaView(PermissionRequiredMixin, View):
    permission_required = 'kardex.change_ficha'
    raise_exception = True

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
        return redirect('kardex:paciente_query')


class FichaTarjetaView(PermissionRequiredMixin, UpdateView):
    template_name = 'kardex/ficha/form_numero_ficha.html'
    model = Ficha
    form_class = FormFichaTarjeta
    success_url = reverse_lazy('kardex:ficha_list')
    permission_required = 'kardex.change_ficha'
    raise_exception = True

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
    export_report_url_name = 'reports:export_ficha_pasivada'

    def get_base_queryset(self):
        return Ficha.objects.filter(pasivado=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Fichas Pasivadas',
            'list_url': reverse_lazy('kardex:ficha_pasivados_list'),
        })
        return context


class FichaHistoryListView(GenericHistoryListView):
    base_model = Ficha
    permission_required = 'kardex.view_ficha'
    template_name = 'kardex/history/list.html'
