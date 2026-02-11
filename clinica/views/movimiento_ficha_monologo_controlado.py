from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.views.generic import TemplateView

from clinica.apis.movimiento_ficha_monologo_controlado import RegistrarSalidaAPI, RegistrarRecepcionAPI
from clinica.forms.movimiento_ficha_monologo_controlado import MovimientoSalidaForm, MovimientoRecepcionForm, \
    FiltroMovimientoForm
from clinica.models.movimiento_ficha_monologo_controlado import MovimientoMonologoControlado


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
            estado='E'
        ).select_related('rut_paciente', 'ficha', 'servicio_clinico_destino', 'profesional')

        # Filtros
        hora_inicio = request.GET.get('hora_inicio')
        hora_termino = request.GET.get('hora_termino')
        servicio_id = request.GET.get('servicio_clinico')
        profesional_nombre = request.GET.get('profesional')

        if hora_inicio:
            qs = qs.filter(fecha_salida__time__gte=hora_inicio)
        if hora_termino:
            qs = qs.filter(fecha_salida__time__lte=hora_termino)
        if servicio_id:
            qs = qs.filter(servicio_clinico_destino_id=servicio_id)
        if profesional_nombre:
            qs = qs.filter(profesional__nombres__icontains=profesional_nombre)

        data = []
        for mov in qs:
            data.append({
                'id': mov.id,
                'rut': mov.rut_paciente.rut,
                'paciente': mov.rut_paciente.nombre_completo,
                'ficha': mov.numero_ficha,
                'servicio_recepcion': mov.servicio_clinico_destino.nombre if mov.servicio_clinico_destino else '-',
                'profesional': str(mov.profesional),
                'observacion': mov.observacion_salida or '',
                'estado': mov.get_estado_display(),
                'fecha': timezone.localtime(mov.fecha_salida).strftime('%d/%m/%Y %H:%M')
            })

        return JsonResponse({'data': data})

    def post(self, request, *args, **kwargs):
        view = RegistrarSalidaAPI.as_view()
        return view(request, *args, **kwargs)


class RecepcionFichaView(LoginRequiredMixin, TemplateView):
    template_name = 'movimiento_ficha_monologo_controlado/recepcion_ficha.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = MovimientoRecepcionForm()
        context['filter_form'] = FiltroMovimientoForm(establecimiento=self.request.user.establecimiento)
        context['columns'] = ['RUT', 'Paciente', 'Ficha', 'Servicio Recepción', 'Profesional',
                              'Observación', 'Estado', 'Fecha']
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
            estado='R'
        ).select_related('rut_paciente', 'ficha', 'servicio_clinico_destino', 'profesional')

        # Filtros
        hora_inicio = request.GET.get('hora_inicio')
        hora_termino = request.GET.get('hora_termino')
        servicio_id = request.GET.get('servicio_clinico')
        profesional_nombre = request.GET.get('profesional')

        # Filtrar por fecha de ENTRADA (Recepción)
        if hora_inicio:
            qs = qs.filter(fecha_entrada__time__gte=hora_inicio)
        if hora_termino:
            qs = qs.filter(fecha_entrada__time__lte=hora_termino)
        if servicio_id:
            qs = qs.filter(servicio_clinico_destino_id=servicio_id)
        if profesional_nombre:
            qs = qs.filter(profesional__nombres__icontains=profesional_nombre)

        data = []
        for mov in qs:
            data.append({
                'id': mov.id,
                'rut': mov.rut_paciente.rut,
                'paciente': mov.rut_paciente.nombre_completo,
                'ficha': mov.numero_ficha,
                'servicio_recepcion': mov.servicio_clinico_destino.nombre if mov.servicio_clinico_destino else '-',
                'profesional': str(mov.profesional),
                'observacion': mov.observacion_entrada or '',  # Observación de recepción
                'estado': mov.get_estado_display(),
                'fecha': timezone.localtime(mov.fecha_entrada).strftime('%d/%m/%Y %H:%M') if mov.fecha_entrada else '-'
            })

        return JsonResponse({'data': data})

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
            estado='E'
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
            estado='E'
        ).select_related('rut_paciente', 'ficha', 'servicio_clinico_destino', 'profesional')

        # Filtros
        hora_inicio = request.GET.get('hora_inicio')
        hora_termino = request.GET.get('hora_termino')
        servicio_id = request.GET.get('servicio_clinico')
        profesional_nombre = request.GET.get('profesional')

        if hora_inicio:
            qs = qs.filter(fecha_salida__time__gte=hora_inicio)
        if hora_termino:
            qs = qs.filter(fecha_salida__time__lte=hora_termino)
        if servicio_id:
            qs = qs.filter(servicio_clinico_destino_id=servicio_id)
        if profesional_nombre:
            qs = qs.filter(profesional__nombres__icontains=profesional_nombre)

        data = []
        now = timezone.now()
        for mov in qs:
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
                'rut': mov.rut_paciente.rut,
                'ficha': mov.numero_ficha,
                'paciente': mov.rut_paciente.nombre_completo,
                'servicio_clinico': mov.servicio_clinico_destino.nombre if mov.servicio_clinico_destino else '-',
                'profesional': str(mov.profesional),
                'fecha_salida': timezone.localtime(mov.fecha_salida).strftime(
                    '%d/%m/%Y %H:%M') if mov.fecha_salida else '-',
                'horas_transito': time_str
            })

        return JsonResponse({'data': data})
