from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Case, When, IntegerField, Value
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from clinica.apis.movimiento_ficha_monologo_controlado import RegistrarSalidaAPI, RegistrarRecepcionAPI, \
    RegistrarTraspasoAPI
from clinica.forms.movimiento_ficha_monologo_controlado import (
    MovimientoSalidaForm, MovimientoRecepcionForm, FiltroMovimientoForm, MovimientoTraspasoForm
)
from clinica.models import Ficha
from clinica.models.movimiento_ficha_monologo_controlado import MovimientoMonologoControlado
from core.utils.search_utils import get_rut_q_filter, get_name_q_filter
from personas.models.pacientes import Paciente


class SalidaFichaView(LoginRequiredMixin, TemplateView):
    template_name = 'movimiento_ficha_monologo_controlado/salida_ficha_update.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Assuming user has establishment
        context['form'] = MovimientoSalidaForm(establecimiento=self.request.user.establecimiento)
        context['filter_form'] = FiltroMovimientoForm(establecimiento=self.request.user.establecimiento)
        # Define columns for the table if needed (template iterates 'columns')
        context['columns'] = ['RUT', 'Paciente', 'Ficha', 'Servicio Recepción', 'Profesional',
                              'Observación', 'Estado', 'Fecha']
        return context

    def get(self, request, *args, **kwargs):
        if request.GET.get('datatable'):
            return self.get_datatable_data(request)
        return super().get(request, *args, **kwargs)

    def get_datatable_data(self, request):
        establecimiento = request.user.establecimiento
        # Salida: Movimientos que han salido (Enviados) desde mi establecimiento (o que están en tránsito en general?)
        # Según la lógica de negocio, se registra una salida.
        # "mandar tambien todos los movimientos que tengan el estado de E enviado"
        # Asumimos que son los generados por el usuario o pertinentes al establecimiento.
        # Pero el Prompt dice "La ficha debe pertenecer al establecimiento del usuario logueado"
        qs = MovimientoMonologoControlado.objects.filter(
            establecimiento=establecimiento,
            estado='E',
            ficha__isnull=False,
            ficha__paciente__isnull=False,
            status=True
        ).select_related('rut_paciente', 'ficha', 'servicio_clinico_destino', 'profesional').order_by('-fecha_salida')

        # Filtros
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_termino = request.GET.get('fecha_termino')
        servicio_id = request.GET.get('servicio_clinico')
        profesional_id = request.GET.get('profesional')

        if fecha_inicio:
            qs = qs.filter(fecha_salida__gte=fecha_inicio)
        if fecha_termino:
            qs = qs.filter(fecha_salida__lte=fecha_termino)
        if servicio_id:
            qs = qs.filter(servicio_clinico_destino_id=servicio_id)
        if profesional_id:
            qs = qs.filter(profesional_id=profesional_id, profesional__establecimiento=establecimiento, status=True)

        # Búsqueda Global (DataTables)
        search_value = request.GET.get('search[value]', '').strip()
        if search_value:
            q = get_rut_q_filter(search_value, 'rut')
            q |= get_rut_q_filter(search_value, 'rut_paciente__rut')
            q |= get_name_q_filter(search_value, 'rut_paciente__')
            q |= Q(numero_ficha__icontains=search_value)
            q |= Q(servicio_clinico_destino__nombre__icontains=search_value)
            q |= Q(profesional__nombres__icontains=search_value)
            q |= Q(observacion_salida__icontains=search_value)
            q |= Q(fecha_salida__icontains=search_value)
            qs = qs.filter(q)

        data = []
        for mov in qs:
            fecha_local = timezone.localtime(mov.fecha_salida)
            edit_url = reverse('movimiento_monologo_salida_update', kwargs={'pk': mov.id})
            estado_badge = ''
            if mov.estado == 'E':
                estado_badge = f'<span class="badge badge-primary">{mov.get_estado_display()}</span>'
            elif mov.estado == 'R':
                estado_badge = f'<span class="badge badge-success">{mov.get_estado_display()}</span>'
            else:
                estado_badge = f'<span class="badge badge-secondary">{mov.get_estado_display()}</span>'

            data.append({
                'id': mov.id,
                'acciones': f'<a href="{edit_url}" class="btn btn-warning btn-sm p-1 " title="Editar"><i class="fas fa-edit"></i></a> '
                            f'<button type="button" class="btn btn-danger btn-sm p-1 btn-delete-movimiento" data-id="{mov.id}" title="Eliminar">'
                            f'<i class="fas fa-trash"></i></button>',
                'rut': mov.ficha.paciente.rut,
                'paciente': mov.ficha.paciente.nombre_completo,
                'ficha': mov.numero_ficha,
                'servicio_recepcion': mov.servicio_clinico_destino.nombre if mov.servicio_clinico_destino else '-',
                'profesional': str(mov.profesional) if mov.profesional else '-',
                'observacion': mov.observacion_salida or '',
                'estado': estado_badge,
                'fecha': fecha_local.strftime('%d/%m/%Y %H:%M'),
                'fecha_iso': fecha_local.isoformat(),
            })

        return JsonResponse({'data': data})

    def post(self, request, *args, **kwargs):
        view = RegistrarSalidaAPI.as_view()
        return view(request, *args, **kwargs)


class TraspasoFichaView(LoginRequiredMixin, TemplateView):
    template_name = 'movimiento_ficha_monologo_controlado/traspaso_ficha.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = MovimientoTraspasoForm(establecimiento=self.request.user.establecimiento)
        context['filter_form'] = FiltroMovimientoForm(establecimiento=self.request.user.establecimiento)
        context['columns'] = ['RUT', 'Paciente', 'Ficha', 'Servicio Destino', 'Profesional',
                              'Observación Traspaso', 'Estado', 'Fecha Salida']
        context['datatable_enabled'] = True
        return context

    def get(self, request, *args, **kwargs):
        if request.GET.get('datatable'):
            return self.get_datatable_data(request)
        return super().get(request, *args, **kwargs)

    def get_datatable_data(self, request):
        establecimiento = request.user.establecimiento
        qs = MovimientoMonologoControlado.objects.filter(
            establecimiento=establecimiento,
            estado='E',
            status=True
        ).select_related('rut_paciente', 'ficha', 'servicio_clinico_destino', 'profesional')

        # Filtros
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_termino = request.GET.get('fecha_termino')
        servicio_id = request.GET.get('servicio_clinico')
        profesional_id = request.GET.get('profesional')

        if fecha_inicio:
            qs = qs.filter(fecha_salida__gte=fecha_inicio)
        if fecha_termino:
            qs = qs.filter(fecha_salida__lte=fecha_termino)
        if servicio_id:
            qs = qs.filter(servicio_clinico_destino_id=servicio_id)
        if profesional_id:
            qs = qs.filter(profesional_id=profesional_id)

        # Total antes de búsqueda global
        records_total = qs.count()
        records_filtered = records_total

        # Búsqueda Global (DataTables)
        search_value = request.GET.get('search[value]', '').strip()
        if search_value:
            q = get_rut_q_filter(search_value, 'rut')
            q |= get_rut_q_filter(search_value, 'rut_paciente__rut')
            q |= get_name_q_filter(search_value, 'rut_paciente__')
            q |= Q(numero_ficha__icontains=search_value)
            q |= Q(servicio_clinico_destino__nombre__icontains=search_value)
            q |= Q(profesional__nombres__icontains=search_value)
            q |= Q(observacion_salida__icontains=search_value)
            q |= Q(fecha_salida__icontains=search_value)
            qs = qs.filter(q)
            records_filtered = qs.count()

        # Ordenamiento
        order_column_index = int(request.GET.get('order[0][column]', 0))
        order_dir = request.GET.get('order[0][dir]', 'desc')
        prefix = '-' if order_dir == 'desc' else ''

        # Mapeo de columnas según el orden en context['columns'] + ID + Acciones
        # 0: ID, 1: acciones, 2: RUT, 3: Paciente, 4: Ficha, 5: Servicio Destino, 6: Profesional, 7: Obs, 8: Estado, 9: Fecha Salida,
        columns_map = {
            0: 'id',
            2: 'rut',
            3: 'rut_paciente__nombres',
            4: 'numero_ficha',
            5: 'servicio_clinico_destino__nombre',
            6: 'profesional__nombres',
            7: 'observacion_traspaso',
            8: 'estado',
            9: 'fecha_salida',
        }

        col_name = columns_map.get(order_column_index)
        if col_name:
            qs = qs.order_by(f'{prefix}{col_name}')
        else:
            qs = qs.order_by('-fecha_salida')

        # Paginación
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        qs_slice = qs[start:start + length]

        data = []
        for mov in qs_slice:
            fecha_salida_local = timezone.localtime(mov.fecha_salida) if mov.fecha_salida else None
            fecha_entrada_local = timezone.localtime(mov.fecha_entrada) if mov.fecha_entrada else None

            estado_badge = ''
            if mov.estado == 'E':
                estado_badge = f'<span class="badge badge-primary">{mov.get_estado_display()}</span>'
            elif mov.estado == 'R':
                estado_badge = f'<span class="badge badge-success">{mov.get_estado_display()}</span>'
            else:
                estado_badge = f'<span class="badge badge-secondary">{mov.get_estado_display()}</span>'

            # El base.html espera campos que coincidan con los nombres en 'columns' (slugified o similar?)
            # Según base.html: {data: 'ID'}, {data: 'actions'}, {data: '{{ col }}'}
            # 'columns' = ['RUT', 'Paciente', 'Ficha', 'Servicio Destino', 'Profesional', 'Observación Traspaso', 'Estado', 'Fecha Salida', 'Fecha Entrada']
            data.append({
                'ID': mov.id,
                'actions': f'<button type="button" class="btn btn-danger btn-sm p-1 btn-delete-movimiento" data-id="{mov.id}" title="Eliminar">'
                           f'<i class="fas fa-trash"></i></button>',
                'RUT': mov.ficha.paciente.rut if mov.ficha and mov.ficha.paciente else mov.rut,
                'Paciente': mov.ficha.paciente.nombre_completo if mov.ficha and mov.ficha.paciente else (
                    mov.rut_paciente.nombre_completo if mov.rut_paciente else '-'),
                'Ficha': mov.numero_ficha,
                'Servicio Destino': mov.servicio_clinico_destino.nombre if mov.servicio_clinico_destino else '-',
                'Profesional': str(mov.profesional) if mov.profesional else '-',
                'Observación Traspaso': mov.observacion_traspaso or '',
                'Estado': estado_badge,
                'Fecha Salida': fecha_salida_local.strftime('%d/%m/%Y %H:%M') if fecha_salida_local else '-',
            })

        return JsonResponse({
            'draw': int(request.GET.get('draw', 1)),
            'recordsTotal': records_total,
            'recordsFiltered': records_filtered,
            'data': data
        })

    def post(self, request, *args, **kwargs):
        view = RegistrarTraspasoAPI.as_view()
        return view(request, *args, **kwargs)


class SalidaFichaUpdateView(SalidaFichaView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        movimiento = get_object_or_404(MovimientoMonologoControlado, pk=self.kwargs.get('pk'))
        context['movimiento'] = movimiento
        context['form'] = MovimientoSalidaForm(
            instance=movimiento,
            establecimiento=self.request.user.establecimiento,
            initial={
                'rut': movimiento.ficha.paciente.rut,
                'nombre': movimiento.ficha.paciente.nombre_completo,
                'ficha': movimiento.ficha.numero_ficha_sistema,
                'ficha_id_hidden': movimiento.ficha_id
            }
        )
        context['is_update'] = True
        return context

    def post(self, request, *args, **kwargs):
        movimiento = get_object_or_404(MovimientoMonologoControlado, pk=self.kwargs.get('pk'))
        form = MovimientoSalidaForm(request.POST, instance=movimiento, establecimiento=request.user.establecimiento)

        if form.is_valid():
            try:
                # El formulario ya maneja los campos y el instance
                # Pero la vista anterior hacia búsqueda manual de ficha por RUT
                rut_paciente = form.cleaned_data.get('rut')
                paciente = Paciente.objects.filter(rut=rut_paciente).first()
                if not paciente:
                    return JsonResponse({'success': False, 'error': 'Paciente no encontrado.'})

                ficha = Ficha.objects.filter(paciente=paciente, establecimiento=request.user.establecimiento).first()
                if not ficha:
                    return JsonResponse({'success': False, 'error': 'Ficha no encontrada para este paciente.'})

                # Guardamos el valor original de fecha_salida antes de que el form lo cambie si viene vacío
                fecha_salida_original = movimiento.fecha_salida

                mov = form.save(commit=False)

                # Si el usuario ingresó una fecha, se actualiza. Si no, se mantiene la original.
                fecha_salida_form = form.cleaned_data.get('fecha_salida')

                if fecha_salida_form:
                    mov.fecha_salida = fecha_salida_form
                else:
                    mov.fecha_salida = fecha_salida_original

                mov.ficha = ficha
                mov.save()
                return JsonResponse({'success': True, 'message': 'Movimiento actualizado correctamente.'})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        else:
            errors = form.errors.as_text()
            return JsonResponse({'success': False, 'error': f'Error en el formulario: {errors}'})


class RecepcionFichaView(LoginRequiredMixin, TemplateView):
    template_name = 'movimiento_ficha_monologo_controlado/recepcion_ficha.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = MovimientoRecepcionForm()
        context['filter_form'] = FiltroMovimientoForm(establecimiento=self.request.user.establecimiento)
        context['columns'] = ['RUT', 'Paciente', 'Ficha', 'Servicio Recepción', 'Profesional',
                              'Observación', 'Estado', 'Envío', 'Recepción']
        return context

    def get(self, request, *args, **kwargs):
        if request.GET.get('datatable'):
            return self.get_datatable_data(request)
        return super().get(request, *args, **kwargs)

    def get_datatable_data(self, request):
        establecimiento = request.user.establecimiento
        # Recepción: Movimientos ya recibidos (estado R) en este establecimiento
        qs = MovimientoMonologoControlado.objects.filter(
            establecimiento=establecimiento,
            estado__in=['E', 'R'], status=True
        ).select_related(
            'rut_paciente',
            'ficha',
            'servicio_clinico_destino',
            'profesional'
        ).annotate(
            estado_orden=Case(
                When(estado='E', then=Value(0)),
                When(estado='R', then=Value(1)),
                output_field=IntegerField()
            )
        ).order_by('estado_orden', '-fecha_salida')

        # Filtros Base (GET)
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_termino = request.GET.get('fecha_termino')
        servicio_id = request.GET.get('servicio_clinico')
        profesional_id = request.GET.get('profesional')

        # Filtrar por fecha de ENTRADA (Recepción)
        if fecha_inicio:
            qs = qs.filter(fecha_entrada__gte=fecha_inicio)
        if fecha_termino:
            qs = qs.filter(fecha_entrada__lte=fecha_termino)
        if servicio_id:
            qs = qs.filter(servicio_clinico_destino_id=servicio_id)
        if profesional_id:
            qs = qs.filter(profesional_id=profesional_id, profesional__establecimiento=establecimiento, status=True)

        # Total antes de búsqueda global
        records_total = qs.count()
        records_filtered = records_total

        # Búsqueda Global (DataTables)
        search_value = request.GET.get('search[value]', '').strip()
        if search_value:
            q = get_rut_q_filter(search_value, 'rut')
            q |= get_rut_q_filter(search_value, 'rut_paciente__rut')
            q |= get_name_q_filter(search_value, 'rut_paciente__')
            q |= Q(numero_ficha__icontains=search_value)
            q |= Q(servicio_clinico_destino__nombre__icontains=search_value)
            q |= Q(profesional__nombres__icontains=search_value)
            q |= Q(observacion_entrada__icontains=search_value)
            q |= Q(fecha_salida__icontains=search_value)
            q |= Q(fecha_entrada__icontains=search_value)
            qs = qs.filter(q)
            records_filtered = qs.count()

        # Ordenamiento
        order_column_index = int(request.GET.get('order[0][column]', 0))
        order_dir = request.GET.get('order[0][dir]', 'desc')
        prefix = '-' if order_dir == 'desc' else ''

        # Mapeo de columnas: 0:id, 1:acc, 2:rut, 3:paciente, 4:ficha, 5:servicio, 6:profesional, 7:obs, 8:estado, 9:fecha_salida, 10:fecha_entrada
        columns_map = {
            0: 'id',
            2: 'rut',
            3: 'rut_paciente__nombres',
            4: 'numero_ficha',
            5: 'servicio_clinico_destino__nombre',
            6: 'profesional__nombres',
            7: 'observacion_entrada',
            8: 'estado',
            9: 'fecha_salida',
            10: 'fecha_entrada'
        }

        col_name = columns_map.get(order_column_index)
        if col_name:
            qs = qs.order_by(f'{prefix}{col_name}')
        else:
            qs = qs.order_by('-fecha_entrada')

        # Paginación
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))

        # Evitar length negativo o excesivo si fuera necesario, aunque slice maneja bien el exceso
        qs_slice = qs[start:start + length]

        data = []
        for mov in qs_slice:
            estado_badge = ''
            if mov.estado == 'E':
                estado_badge = f'<span class="badge badge-primary">{mov.get_estado_display()}</span>'
            elif mov.estado == 'R':
                estado_badge = f'<span class="badge badge-success">{mov.get_estado_display()}</span>'
            else:
                estado_badge = f'<span class="badge badge-secondary">{mov.get_estado_display()}</span>'

            data.append({
                'id': mov.id,
                'acciones': f'<button type="button" class="btn btn-danger btn-sm p-1 btn-delete-movimiento" data-id="{mov.id}" title="Eliminar">'
                            f'<i class="fas fa-trash"></i></button>',
                'rut': mov.rut,
                'paciente': mov.rut_paciente.nombre_completo if mov.rut_paciente else '-',
                'ficha': mov.numero_ficha,
                'servicio_recepcion': mov.servicio_clinico_destino.nombre if mov.servicio_clinico_destino else '-',
                'profesional': str(mov.profesional) if mov.profesional else '-',
                'observacion': mov.observacion_entrada or '',  # Observación de recepción
                'estado': estado_badge,
                'fecha_salida': timezone.localtime(mov.fecha_salida).strftime(
                    '%d/%m/%Y %H:%M') if mov.fecha_salida else '-',
                'fecha_entrada': timezone.localtime(mov.fecha_entrada).strftime(
                    '%d/%m/%Y %H:%M') if mov.fecha_entrada else '-'
            })

        return JsonResponse({
            'draw': int(request.GET.get('draw', 1)),
            'recordsTotal': records_total,
            'recordsFiltered': records_filtered,
            'data': data
        })

    def post(self, request, *args, **kwargs):
        view = RegistrarRecepcionAPI.as_view()
        return view(request, *args, **kwargs)


class FichasEnTransitoView(LoginRequiredMixin, TemplateView):
    template_name = 'movimiento_ficha_monologo_controlado/tabla_transito_ficha_update.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        establecimiento = self.request.user.establecimiento

        # Contar total en tránsito (Estado E)
        total = MovimientoMonologoControlado.objects.filter(
            establecimiento=establecimiento,
            estado='E',
            status=True
        ).count()

        context['title'] = f'Fichas en Tránsito (Total: {total})'
        context['total_transito'] = total
        context['filter_form'] = FiltroMovimientoForm(establecimiento=establecimiento)
        # Columnas para la tabla
        context['columns'] = ['RUT', 'Ficha', 'Paciente', 'Servicio Clínico', 'Profesional', 'Fecha Salida',
                              'Horas en Tránsito']
        return context

    def get(self, request, *args, **kwargs):
        if request.GET.get('datatable'):
            return self.get_datatable_data(request)
        return super().get(request, *args, **kwargs)

    def get_datatable_data(self, request):
        establecimiento = request.user.establecimiento
        # Movimientos en tránsito (E)
        qs = MovimientoMonologoControlado.objects.filter(
            establecimiento=establecimiento,
            estado='E',
            status=True
        ).select_related('rut_paciente', 'ficha', 'servicio_clinico_destino', 'profesional')

        # Filtros Base
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_termino = request.GET.get('fecha_termino')
        servicio_id = request.GET.get('servicio_clinico')
        profesional_id = request.GET.get('profesional')

        if fecha_inicio:
            qs = qs.filter(fecha_salida__gte=fecha_inicio)
        if fecha_termino:
            qs = qs.filter(fecha_salida__lte=fecha_termino)
        if servicio_id:
            qs = qs.filter(servicio_clinico_destino_id=servicio_id)
        if profesional_id:
            qs = qs.filter(profesional_id=profesional_id, profesional__establecimiento=establecimiento, status=True)

        # Total antes de búsqueda
        records_total = qs.count()
        records_filtered = records_total

        # Búsqueda Global (DataTables)
        search_value = request.GET.get('search[value]', '').strip()
        if search_value:
            q = get_rut_q_filter(search_value, 'rut')
            q |= get_rut_q_filter(search_value, 'rut_paciente__rut')
            q |= get_name_q_filter(search_value, 'rut_paciente__')
            q |= Q(numero_ficha__icontains=search_value)
            q |= Q(servicio_clinico_destino__nombre__icontains=search_value)
            q |= Q(profesional__nombres__icontains=search_value)
            q |= Q(fecha_salida__icontains=search_value)
            qs = qs.filter(q)
            records_filtered = qs.count()

        # Ordenamiento
        order_column_index = int(request.GET.get('order[0][column]', 0))
        order_dir = request.GET.get('order[0][dir]', 'desc')
        prefix = '-' if order_dir == 'desc' else ''

        # Columnas: 0:id, 1:acc, 2:rut, 3:ficha, 4:paciente, 5:servicio, 6:profesional, 7:fecha_salida, 8:horas
        columns_map = {
            0: 'id',
            2: 'rut',
            3: 'numero_ficha',
            4: 'rut_paciente__nombres',
            5: 'servicio_clinico_destino__nombre',
            6: 'profesional__nombres',
            7: 'fecha_salida'
        }

        # Manejo especial para columna 8 (Horas en tránsito)
        # Horas = Now - Fecha Salida. Mayor horas => Menor fecha salida.
        # Si order_dir 'asc' (menor horas primero) => Mayor fecha salida (más reciente) primero => DESC fecha_salida
        # Si order_dir 'desc' (mayor horas primero) => Menor fecha salida (más antigua) primero => ASC fecha_salida
        if order_column_index == 8:
            if order_dir == 'asc':
                qs = qs.order_by('-fecha_salida')
            else:
                qs = qs.order_by('fecha_salida')
        else:
            col_name = columns_map.get(order_column_index)
            if col_name:
                qs = qs.order_by(f'{prefix}{col_name}')
            else:
                qs = qs.order_by('-fecha_salida')

        # Paginación
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))

        qs_slice = qs[start:start + length]

        data = []
        now = timezone.now()
        for mov in qs_slice:
            # Calcular horas en tránsito
            if mov.fecha_salida:
                diff = now - mov.fecha_salida
                total_seconds = int(diff.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                time_str = f"{hours}h {minutes}m"
            else:
                time_str = "-"

            data.append({
                'id': mov.id,
                'acciones': f'<button type="button" class="btn btn-danger btn-sm p-1 btn-delete-movimiento" data-id="{mov.id}" title="Eliminar">'
                            f'<i class="fas fa-trash"></i></button>',
                'rut': mov.rut,
                'ficha': mov.numero_ficha,
                'paciente': mov.rut_paciente.nombre_completo if mov.rut_paciente else '-',
                'servicio_clinico': mov.servicio_clinico_destino.nombre if mov.servicio_clinico_destino else '-',
                'profesional': str(mov.profesional) if mov.profesional else '-',
                'fecha_salida': timezone.localtime(mov.fecha_salida).strftime(
                    '%d/%m/%Y %H:%M') if mov.fecha_salida else '-',
                'horas_transito': time_str
            })

        return JsonResponse({
            'draw': int(request.GET.get('draw', 1)),
            'recordsTotal': records_total,
            'recordsFiltered': records_filtered,
            'data': data
        })
