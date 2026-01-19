from datetime import datetime

from django.contrib import messages
from django.db import transaction, IntegrityError
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, DetailView

from clinica.forms.ficha import FichaForm
from clinica.models import Ficha
from core.mixin import DataTableMixin
from personas.forms.pacientes import PacienteForm
from personas.models.pacientes import Paciente


def capturar_datos_paciente(request):
    def get_bool(field):
        return request.POST.get(field) in ['on', 'true', 'True', True, '1']

    return {
        "paciente_id": request.POST.get('paciente_id'),
        "rut": request.POST.get('rut'),
        "nombre": request.POST.get('nombre'),
        "apellido_paterno": request.POST.get('apellido_paterno'),
        "apellido_materno": request.POST.get('apellido_materno'),
        "nombre_social": request.POST.get('nombre_social'),
        "pasaporte": request.POST.get('pasaporte'),
        "nip": request.POST.get('nip'),

        "fecha_nacimiento": request.POST.get('fecha_nacimiento'),
        "sexo": request.POST.get('sexo'),
        "genero_id": request.POST.get('genero'),
        "estado_civil": request.POST.get('estado_civil'),

        "recien_nacido": get_bool('recien_nacido'),
        "extranjero": get_bool('extranjero'),
        "pueblo_indigena": get_bool('pueblo_indigena'),
        "fallecido": get_bool('fallecido'),
        "fecha_fallecimiento": request.POST.get('fecha_fallecimiento'),

        "rut_madre": request.POST.get('rut_madre'),
        "nombres_madre": request.POST.get('nombres_madre'),
        "nombres_padre": request.POST.get('nombres_padre'),
        "nombre_pareja": request.POST.get('nombre_pareja'),
        "representante_legal": request.POST.get('representante_legal'),
        "rut_responsable_temporal": request.POST.get('rut_responsable_temporal'),
        "usar_rut_madre_como_responsable": get_bool('usar_rut_madre_como_responsable'),

        "direccion": request.POST.get('direccion'),
        "comuna": request.POST.get('comuna'),
        "ocupacion": request.POST.get('ocupacion'),
        "sin_telefono": get_bool('sin_telefono'),
        "numero_telefono1": request.POST.get('numero_telefono1'),
        "numero_telefono2": request.POST.get('numero_telefono2'),

        # FICHAS
        "ficha": request.POST.get('ficha'),
    }


def parse_fecha(fecha_str):
    if not fecha_str:
        return None
    try:
        return datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def paciente_view(request, paciente_id=None):
    paciente_instance = None
    ficha_instance = None
    modo = "consulta"

    if request.method == 'POST':
        # if request.method == 'POST':
        #     print("========== POST RAW ==========")
        #     for k, v in request.POST.items():
        #         print(f"{k} = {v}")
        #     print("================================")

        accion = request.POST.get('accion')
        paciente_id_post = request.POST.get('paciente_id') or paciente_id
        es_edicion = (accion == 'ACTUALIZAR') or bool(paciente_id_post)

        if es_edicion and paciente_id_post:
            paciente_instance = Paciente.objects.filter(pk=paciente_id_post).first()

            if paciente_instance:
                ficha_instance = Ficha.objects.filter(
                    paciente=paciente_instance,
                    establecimiento=request.user.establecimiento
                ).first()

        paciente_form = PacienteForm(request.POST, instance=paciente_instance)
        ficha_form = FichaForm(request.POST, instance=ficha_instance)

        if paciente_form.is_valid() and ficha_form.is_valid():

            # Verificación de consistencia Accion vs Instancia
            rut_post = paciente_form.cleaned_data.get('rut')
            if accion == 'CREAR':
                if Paciente.objects.filter(rut=rut_post).exists():
                    paciente_form.add_error('rut',
                                            'Ya existe un paciente con este RUT. Por favor, consúltelo antes de intentar crear uno nuevo.')
                    return render(request, 'paciente/form.html', {
                        'paciente_form': paciente_form,
                        'ficha_form': ficha_form,
                        'modo': 'error_crear',
                        'accion': accion,
                        'paciente_id': paciente_id_post,
                        'title': 'Consulta de pacientes'
                    })
            elif accion == 'ACTUALIZAR':
                if not paciente_instance:
                    messages.error(request,
                                   'Error de consistencia: Se intentó actualizar un paciente que no existe o no fue cargado correctamente.')
                    return redirect('paciente_view')

            try:

                with transaction.atomic():

                    paciente = paciente_form.save(commit=False)
                    es_creacion = paciente.pk is None

                    paciente.usuario_modifica = request.user
                    paciente.save()

                    ficha = ficha_form.save(commit=False)
                    ficha.paciente = paciente
                    ficha.establecimiento = request.user.establecimiento
                    ficha.usuario = request.user
                    ficha.save()

            except IntegrityError:
                ficha_form.add_error(
                    'numero_ficha_sistema',
                    'Ya existe una ficha con este número para este establecimiento.'
                )
                messages.error(request, 'El número de ficha que intentas agregar ya fue asignado a otro paciente.')

                modo = "error_actualizar" if es_edicion else "error_crear"

                return render(request, 'paciente/form.html', {
                    'paciente_form': paciente_form,
                    'ficha_form': ficha_form,
                    'modo': modo,
                    'accion': accion,
                    'paciente_id': paciente_id_post,
                    'title': 'Consulta de pacientes'
                })

            # ÉXITO
            if es_creacion:
                messages.success(request, 'Paciente y ficha creados correctamente.')
                modo = "creado"
            else:
                messages.info(request, 'Paciente y ficha actualizados correctamente.')
                modo = "actualizado"

            return redirect('paciente_view_param', paciente_id=paciente.id)

        else:
            # ERRORES DE VALIDACIÓN
            messages.error(request, 'Por favor corrige los errores.')
            modo = "error_actualizar" if es_edicion else "error_crear"

    if request.method == 'GET':
        # GET
        if paciente_id:
            paciente_instance = Paciente.objects.filter(pk=paciente_id).first()

            if paciente_instance:
                ficha_instance = Ficha.objects.filter(
                    paciente=paciente_instance,
                    establecimiento=request.user.establecimiento
                ).first()

        paciente_form = PacienteForm(instance=paciente_instance)
        ficha_form = FichaForm(instance=ficha_instance)

    return render(request, 'paciente/form.html', {
        'paciente_form': paciente_form,
        'ficha_form': ficha_form,
        'modo': modo,
        'accion': request.POST.get('accion', 'ACTUALIZAR' if paciente_id else 'CREAR'),
        'paciente_id': request.POST.get('paciente_id', paciente_id),
        'title': 'Consulta de pacientes'
    })


class PacienteListView(DataTableMixin, TemplateView):
    template_name = 'paciente/list.html'
    model = Paciente
    datatable_columns = ['ID', 'N° Ficha', 'RUT', 'Nombre', 'Sexo', 'Estado Civil', 'Comuna', 'Observación']
    datatable_order_fields = [
        'id',
        None,
        'rut',
        None,
        'sexo',
        'estado_civil',
        'comuna__nombre',
        None,
    ]

    datatable_search_fields = [
        'rut__icontains',
        'nombre__icontains',
        'apellido_paterno__icontains',
        'apellido_materno__icontains',
        'sexo__icontains',
        'estado_civil__icontains',
        'comuna__nombre__icontains',
    ]

    url_detail = 'paciente_detail'
    url_update = 'paciente_view_param'

    def get_base_queryset(self):
        # Vista libre: no limitar por establecimiento, mostrar todos los pacientes
        return Paciente.objects.filter(status='ACTIVE')

    def render_row(self, obj):
        nombre_completo = f"{(obj.nombre or '').upper()} {(obj.apellido_paterno or '').upper()} {(obj.apellido_materno or '').upper()}".strip()
        ficha = Ficha.objects.filter(paciente=obj, establecimiento=self.request.user.establecimiento).first()

        return {
            'ID': obj.id,
            'N° Ficha': (str(ficha.numero_ficha_sistema) if ficha and ficha.numero_ficha_sistema else 'SIN FICHA'),
            'RUT': obj.rut or 'Sin RUT',
            'Nombre': nombre_completo or 'Sin Nombre',
            'Sexo': obj.sexo or '',
            'Estado Civil': obj.estado_civil or '',
            'Comuna': (getattr(obj.comuna, 'nombre', '') or '').upper(),
            'Observación': (ficha.observacion.lower() if ficha and ficha.observacion else 'SIN OBSERVACIÓN'),
        }

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
            return self.get_datatable_response(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Pacientes',
            'list_url': reverse_lazy('paciente_list'),
            'create_url': reverse_lazy('paciente_query'),
            'datatable_enabled': True,
            'datatable_order': [[0, 'desc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
            'export_csv_url': reverse_lazy('export_paciente_csv'),
        })
        return context


class PacienteDetailView(DetailView):
    model = Paciente
    template_name = 'kardex/paciente/detail.html'
    permission_required = 'kardex.view_paciente'
    raise_exception = True

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class PacienteRecienNacidoListView(PacienteListView):
    datatable_columns = [
        'ID',
        'Código',
        'N° Ficha',
        'Nombre',
        'Apellidos',
        'F. Nacimiento',
        'Sexo',
        'Rut Responsable',
        'Comuna',
        'Observación',
    ]

    datatable_order_fields = [
        'id',
        'codigo',
        None,
        'nombre',
        None,
        'fecha_nacimiento',
        'sexo',
        'rut_responsable_temporal',
        'comuna__nombre',
        None,
    ]

    datatable_search_fields = [
        'codigo__icontains',
        'rut__icontains',
        'nombre__icontains',
        'apellido_paterno__icontains',
        'apellido_materno__icontains',
        'sexo__icontains',
        'rut_responsable_temporal__icontains',
        'comuna__nombre__icontains',
    ]

    def render_row(self, obj):
        apellidos = f"{obj.apellido_paterno or ''} {obj.apellido_materno or ''}".strip()
        ficha = Ficha.objects.filter(paciente=obj, establecimiento=self.request.user.establecimiento).first()

        return {
            'ID': obj.id,
            'Código': (obj.codigo or '').upper(),
            'N° Ficha': (str(ficha.numero_ficha_sistema) if ficha and ficha.numero_ficha_sistema else 'SIN FICHA'),
            'Nombre': (obj.nombre or '').upper(),
            'Apellidos': apellidos.upper(),
            'F. Nacimiento': obj.fecha_nacimiento.strftime('%d/%m/%Y') if obj.fecha_nacimiento else '---',
            'Sexo': (obj.sexo or '').upper(),
            'Rut Responsable': (
                obj.rut_responsable_temporal.upper()
                if obj.rut_responsable_temporal and obj.rut_responsable_temporal.lower() != 'nan'
                else 'SIN RUT'
            ),
            'Comuna': (getattr(obj.comuna, 'nombre', '') or '').upper(),
            'Observación': (ficha.observacion.lower() if ficha and ficha.observacion else 'SIN OBSERVACIÓN'),
        }

    def get_base_queryset(self):
        return Paciente.objects.filter(recien_nacido=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Pacientes Recién Nacidos',
            'list_url': reverse_lazy('paciente_recien_nacido_list'),
            'export_csv_url': reverse_lazy('export_paciente_recien_nacido_csv'),
        })
        return context


class PacienteExtranjeroListView(PacienteListView):
    datatable_columns = ['ID', 'N° Ficha', 'Código', 'RUT', 'Nombre', 'NIP', 'Pasaporte', 'Sexo', 'Estado Civil',
                         'Comuna',
                         'Previsión', 'Observación']
    datatable_order_fields = [
        'id',
        None,
        'codigo',
        'rut',
        'nombre',
        'nip',
        'pasaporte',
        'sexo',
        'estado_civil',
        'comuna__nombre',
        'prevision__nombre',
        None
    ]

    datatable_search_fields = [
        'codigo__icontains',
        'rut__icontains',
        'nombre__icontains',
        'nip__icontains',
        'pasaporte__icontains',
        'apellido_paterno__icontains',
        'apellido_materno__icontains',
        'sexo__icontains',
        'estado_civil__icontains',
        'comuna__nombre__icontains',
        'prevision__nombre__icontains'
    ]

    def render_row(self, obj):
        ficha = Ficha.objects.filter(paciente=obj, establecimiento=self.request.user.establecimiento).first()
        return {
            'ID': obj.id,
            'N° Ficha': (str(ficha.numero_ficha_sistema) if ficha and ficha.numero_ficha_sistema else 'SIN FICHA'),
            'Código': (obj.codigo or '').upper(),
            'RUT': (obj.rut or '').upper(),
            'Nombre': (obj.nombre or '').upper(),
            'NIP': (obj.nip or '').upper(),
            'Pasaporte': (obj.pasaporte or '').upper(),
            'Sexo': (obj.sexo or '').upper(),
            'Estado Civil': (obj.estado_civil or '').upper(),
            'Comuna': (getattr(obj.comuna, 'nombre', '') or '').upper(),
            'Previsión': (getattr(obj.prevision, 'nombre', '') or '').upper(),
            'Observación': (ficha.observacion.lower() if ficha and ficha.observacion else 'SIN OBSERVACIÓN'),
        }

    def get_base_queryset(self):
        return Paciente.objects.filter(extranjero=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Pacientes Extranjeros',
            'list_url': reverse_lazy('kardex:paciente_extranjero_list'),
            'export_csv_url': reverse_lazy('reports:export_paciente_extranjero_csv'),
        })
        return context


class PacienteRutMadreListView(PacienteListView):
    datatable_columns = ['ID', 'N° Ficha', 'Código', 'Nombre', 'Sexo', 'Rut Responsable', 'Comuna', 'Previsión',
                         'Observación']
    datatable_order_fields = [
        'id',
        None,
        'codigo',
        'nombre',
        'sexo',
        'rut_responsable_temporal',
        'comuna__nombre',
        'prevision__nombre',
        None
    ]

    datatable_search_fields = [
        'codigo__icontains',
        'rut__icontains',
        'nombre__icontains',
        'apellido_paterno__icontains',
        'apellido_materno__icontains',
        'sexo__icontains',
        'rut_responsable_temporal__icontains',
        'comuna__nombre__icontains',
        'prevision__nombre__icontains'
    ]

    def render_row(self, obj):
        ficha = Ficha.objects.filter(paciente=obj, establecimiento=self.request.user.establecimiento).first()
        return {
            'ID': obj.id,
            'N° Ficha': (str(ficha.numero_ficha_sistema) if ficha and ficha.numero_ficha_sistema else 'SIN FICHA'),
            'Código': (obj.codigo or '').upper(),
            'Nombre': (obj.nombre or '').upper(),
            'Sexo': (obj.sexo or '').upper(),
            'Rut Responsable': (
                obj.rut_responsable_temporal.upper()
                if obj.rut_responsable_temporal and obj.rut_responsable_temporal.lower() != 'nan'
                else 'SIN RUT'
            ),
            'Comuna': (getattr(obj.comuna, 'nombre', '') or '').upper(),
            'Previsión': (getattr(obj.prevision, 'nombre', '') or '').upper(),
            'Observación': (ficha.observacion.lower() if ficha and ficha.observacion else 'SIN OBSERVACIÓN'),
        }

    def get_base_queryset(self):
        return Paciente.objects.filter(usar_rut_madre_como_responsable=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Pacientes que utilizan el rut de la madre como reponsable',
            'list_url': reverse_lazy('kardex:paciente_rut_madre_list'),
        })
        return context


class PacienteFallecidoListView(PacienteListView):
    datatable_columns = ['ID', 'N° Ficha', 'RUT', 'Nombre', 'Apellidos', 'F. Fallecimiento', 'Sexo', 'Estado Civil',
                         'Comuna', 'Observación']
    datatable_order_fields = [
        'id',
        None,
        'rut',
        'nombre',
        None,
        'fecha_fallecimiento',
        'sexo',
        'estado_civil',
        'comuna__nombre',
        None,
    ]

    datatable_search_fields = [
        'rut__icontains',
        'nombre__icontains',
        'apellido_paterno__icontains',
        'apellido_materno__icontains',
        'sexo__icontains',
        'estado_civil__icontains',
        'comuna__nombre__icontains',
    ]

    def get_base_queryset(self):
        return Paciente.objects.filter(fallecido=True)

    def render_row(self, obj):
        apellidos = f"{obj.apellido_paterno or ''} {obj.apellido_materno or ''}".strip()
        ficha = Ficha.objects.filter(paciente=obj, establecimiento=self.request.user.establecimiento).first()

        return {
            'ID': obj.id,
            'N° Ficha': (str(ficha.numero_ficha_sistema) if ficha and ficha.numero_ficha_sistema else 'SIN FICHA'),
            'RUT': (obj.rut or '').upper(),
            'Nombre': (obj.nombre or '').upper(),
            'Apellidos': apellidos.upper(),
            'F. Fallecimiento': obj.fecha_fallecimiento.strftime('%d/%m/%Y') if obj.fecha_fallecimiento else '---',
            'Sexo': (obj.sexo or '').upper(),
            'Estado Civil': (obj.estado_civil or '').upper(),
            'Comuna': (getattr(obj.comuna, 'nombre', '') or '').upper(),
            'Observación': (ficha.observacion.lower() if ficha and ficha.observacion else 'SIN OBSERVACIÓN'),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Pacientes Fallecidos',
            'list_url': reverse_lazy('kardex:paciente_fallecido_list'),
            'export_csv_url': reverse_lazy('reports:export_paciente_fallecido_csv'),
        })
        return context


class PacientePuebloIndigenaListView(PacienteListView):
    datatable_columns = ['ID', 'N° Ficha', 'RUT', 'Nombre', 'Sexo', 'Estado Civil', 'Comuna', 'Observación']

    def render_row(self, obj):
        ficha = Ficha.objects.filter(paciente=obj, establecimiento=self.request.user.establecimiento).first()
        nombre_completo = f"{(obj.nombre or '').upper()} {(obj.apellido_paterno or '').upper()} {(obj.apellido_materno or '').upper()}".strip()

        return {
            'ID': obj.id,
            'N° Ficha': (str(ficha.numero_ficha_sistema) if ficha and ficha.numero_ficha_sistema else 'SIN FICHA'),
            'RUT': obj.rut or 'Sin RUT',
            'Nombre': nombre_completo or 'Sin Nombre',
            'Sexo': obj.sexo or '',
            'Estado Civil': obj.estado_civil or '',
            'Comuna': (getattr(obj.comuna, 'nombre', '') or '').upper(),
            'Observación': (ficha.observacion.lower() if ficha and ficha.observacion else 'SIN OBSERVACIÓN'),
        }

    def get_base_queryset(self):
        return Paciente.objects.filter(pueblo_indigena=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Pacientes Pertenecientes a Pueblos Indigenas',
            'list_url': reverse_lazy('kardex:paciente_pueblo_indigena_list'),
            'export_csv_url': reverse_lazy('reports:export_paciente_pueblo_indigena_csv'),
        })
        return context
