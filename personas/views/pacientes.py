from datetime import datetime

from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import Count, Subquery
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.dateparse import parse_date
from django.views import View
from django.views.generic import TemplateView, DetailView, FormView

from clinica.forms.ficha import FichaForm
from clinica.models import Ficha
from clinica.models.movimiento_ficha_monologo_controlado import MovimientoMonologoControlado
from core.history import GenericHistoryListView
from core.mixin import DataTableMixin
from personas.forms.pacientes import PacienteForm, PacienteFechaRangoForm
from personas.models.pacientes import Paciente
from respaldos.models.respaldo_ficha import RespaldoFicha as RespaldoFicha
from respaldos.models.respaldo_movimiento import RespaldoMovimientoMonologoControlado
from respaldos.models.respaldo_paciente import RespaldoPaciente


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


def resolver_paciente(paciente_id=None, rut=None):
    """
    Busca un paciente por ID y por RUT, validando consistencia.
    Casos posibles:
    A) PK y RUT existen y corresponden al mismo paciente -> actualización
    B) PK existe pero el RUT corresponde a otro paciente distinto -> actualización (prevalece el del RUT)
    C) No viene PK pero sí existe un paciente con ese RUT -> actualización
    D) No existe ni PK ni RUT -> creación
    """
    paciente_por_id = None
    paciente_por_rut = None

    if paciente_id:
        paciente_por_id = Paciente.objects.filter(pk=paciente_id, status=True).first()

    if rut:
        paciente_por_rut = Paciente.objects.filter(rut=rut, status=True).first()

    # Evaluación de resultados
    if paciente_por_id and paciente_por_rut:
        if paciente_por_id == paciente_por_rut:
            # Caso A: Ambos identifican al mismo paciente
            return paciente_por_id, 'ACTUALIZAR', None
        else:
            # Caso B: Conflicto. Se indica que el RUT manda según requerimiento:
            # "En el caso B es el RUT el que vale por ende se modifica el registro que tiene el rut asignado"
            return paciente_por_rut, 'ACTUALIZAR', None

    if paciente_por_rut:
        # Caso C: Solo RUT existe (o PK no venía)
        return paciente_por_rut, 'ACTUALIZAR', None

    if paciente_por_id:
        # Existe el ID pero el RUT no está en la BD (o no vino RUT)
        return paciente_por_id, 'ACTUALIZAR', None

    # Caso D: Nada encontrado
    return None, 'CREAR', None


def resolver_ficha(ficha_id=None, numero_ficha_sistema=None, establecimiento=None, paciente=None):
    """
    Busca una ficha por ID y por (numero_ficha_sistema + establecimiento).
    """
    ficha_por_id = None
    ficha_por_numero = None

    if ficha_id:
        ficha_por_id = Ficha.objects.filter(pk=ficha_id, status=True).first()

    if numero_ficha_sistema and establecimiento:
        ficha_por_numero = Ficha.objects.filter(
            numero_ficha_sistema=numero_ficha_sistema,
            establecimiento=establecimiento,
            status=True
        ).first()

    # Si no se encuentra por número, buscar si el paciente ya tiene una ficha en este establecimiento
    if not ficha_por_numero and paciente and establecimiento:
        ficha_por_numero = Ficha.objects.filter(
            paciente=paciente,
            establecimiento=establecimiento,
            status=True
        ).first()

    if ficha_por_id and ficha_por_numero:
        if ficha_por_id == ficha_por_numero:
            return ficha_por_id, 'ACTUALIZAR', None
        else:
            # Caso B para Ficha: Prevalece la ficha encontrada por lógica de negocio
            # (número de ficha o paciente en el establecimiento)
            return ficha_por_numero, 'ACTUALIZAR', None

    if ficha_por_numero:
        return ficha_por_numero, 'ACTUALIZAR', None

    if ficha_por_id:
        return ficha_por_id, 'ACTUALIZAR', None

    return None, 'CREAR', None


def paciente_view(request, paciente_id=None):
    paciente_instance = None
    ficha_instance = None
    modo = "consulta"

    if request.method == 'POST':
        # capturamos datos del post
        datos_post = capturar_datos_paciente(request)
        accion_post = request.POST.get('accion')
        rut_post = datos_post.get('rut')
        paciente_id_post = request.POST.get('paciente_id') or paciente_id

        ficha_id_post = request.POST.get('ficha_id')  # Asegurarse que venga del form
        numero_ficha_post = request.POST.get('numero_ficha_sistema')

        # 1. RESOLVER PACIENTE
        paciente_instance, modo_paciente, error_pac_consistencia = resolver_paciente(
            paciente_id=paciente_id_post,
            rut=rut_post
        )

        # 2. RESOLVER FICHA
        ficha_instance, modo_ficha, error_ficha_consistencia = resolver_ficha(
            ficha_id=ficha_id_post,
            numero_ficha_sistema=numero_ficha_post,
            establecimiento=request.user.establecimiento,
            paciente=paciente_instance
        )

        es_edicion = (modo_paciente == 'ACTUALIZAR') or (paciente_instance is not None)
        accion = accion_post or modo_paciente  # Prioridad a lo que venga del POST explicitamente si aplica

        paciente_form = PacienteForm(request.POST, instance=paciente_instance)
        ficha_form = FichaForm(request.POST, instance=ficha_instance, user=request.user)

        if paciente_form.is_valid() and ficha_form.is_valid():
            try:
                with transaction.atomic():
                    # GUARDAR PACIENTE
                    paciente = paciente_form.save(commit=False)
                    es_creacion_paciente = (paciente.pk is None)

                    if es_creacion_paciente:
                        paciente.created_by = request.user
                    paciente.updated_by = request.user
                    paciente.save()

                    # GUARDAR FICHA
                    ficha = ficha_form.save(commit=False)
                    es_creacion_ficha = (ficha.pk is None)

                    if es_creacion_ficha:
                        ficha.created_by = request.user
                    ficha.updated_by = request.user

                    ficha.paciente = paciente
                    ficha.establecimiento = request.user.establecimiento
                    ficha.usuario = request.user
                    ficha.save()

            except IntegrityError as e:
                error_str = str(e).lower()
                if 'unique_paciente_por_establecimiento' in error_str or 'paciente_id' in error_str:
                    ficha_form.add_error(
                        'paciente',
                        'El paciente ya tiene una ficha asignada en este establecimiento.'
                    )
                    messages.error(request, 'Este paciente ya cuenta con una ficha en el establecimiento actual.')
                else:
                    ficha_form.add_error(
                        'numero_ficha_sistema',
                        'La ficha se está intentando duplicar. Bórrela para generar una automática o coloque una válida (que no esté ocupada).'
                    )
                    messages.error(request, 'El número de ficha que intentas agregar ya fue asignado a otro paciente.')

                # Si ya existía el paciente (paciente_instance no es None) o si accion es ACTUALIZAR, es una actualización fallida
                modo = "error_actualizar" if es_edicion else "error_crear"

                return render(request, 'paciente/form.html', {
                    'paciente_form': paciente_form,
                    'ficha_form': ficha_form,
                    'modo': modo,
                    'accion': accion,
                    'paciente_id': paciente_id_post or (paciente_instance.pk if paciente_instance else None),
                    'title': f'Consulta de pacientes {request.user.establecimiento}'
                })

            # ÉXITO
            if es_creacion_paciente:
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

            return render(request, 'paciente/form.html', {
                'paciente_form': paciente_form,
                'ficha_form': ficha_form,
                'modo': modo,
                'accion': accion,
                'paciente_id': paciente_id_post or (paciente_instance.pk if paciente_instance else None),
                'title': f'Consulta de pacientes {request.user.establecimiento}'
            })

    if request.method == 'GET':
        # GET
        if paciente_id:
            paciente_instance, _, _ = resolver_paciente(paciente_id=paciente_id)

            if paciente_instance:
                ficha_instance, _, _ = resolver_ficha(
                    paciente=paciente_instance,
                    establecimiento=request.user.establecimiento
                )

        paciente_form = PacienteForm(instance=paciente_instance)
        ficha_form = FichaForm(instance=ficha_instance, user=request.user)

    return render(request, 'paciente/form.html', {
        'paciente_form': paciente_form,
        'ficha_form': ficha_form,
        'modo': modo,
        'accion': request.POST.get('accion', 'ACTUALIZAR' if (paciente_id or paciente_instance) else 'CREAR'),
        'paciente_id': request.POST.get('paciente_id',
                                        paciente_id or (paciente_instance.pk if paciente_instance else None)),
        'title': f'Consulta de pacientes {request.user.establecimiento}'
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

    def get_url_delete(self):
        user = self.request.user
        if getattr(user, 'rol', None) and getattr(user.rol, 'paciente', None) == 2:
            return 'paciente_delete'
        return None

    def get_base_queryset(self):
        # Vista libre: no limitar por establecimiento, mostrar todos los pacientes
        return Paciente.objects.filter(status=True).order_by('nombre')

    def render_row(self, obj):
        nombre_completo = f"{(obj.nombre or '').upper()} {(obj.apellido_paterno or '').upper()} {(obj.apellido_materno or '').upper()}".strip()
        ficha = Ficha.objects.filter(paciente=obj, establecimiento=self.request.user.establecimiento,
                                     status=True).first()

        return {
            'ID': obj.id,
            'N° Ficha': (str(ficha.numero_ficha_sistema) if ficha and ficha.numero_ficha_sistema else 'SIN FICHA'),
            'RUT': obj.rut or 'Sin RUT',
            'Nombre': nombre_completo or 'Sin Nombre',
            'Sexo': obj.sexo or '',
            'Estado Civil': obj.get_estado_civil_display() or '',
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
            'datatable_order': [[3, 'asc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
            'export_csv_url': reverse_lazy('export_paciente_csv'),
        })
        return context


class PacienteDetailView(DetailView):
    model = Paciente
    template_name = 'paciente/detail.html'
    permission_required = 'view_paciente'

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string(self.template_name, context=context, request=self.request)
            return HttpResponse(html)
        return super().render_to_response(context, **response_kwargs)


class PacienteRecienNacidoListView(PacienteListView):
    datatable_columns = [
        'ID',
        'RUT',
        'N° Ficha',
        'Nombre',
        'Apellidos',
        'Fecha Nacimiento',
        'Sexo',
        'Rut Responsable',
        'Comuna',
        'Observación',
    ]

    datatable_order_fields = [
        'id',
        None,
        'rut',
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
        'rut__icontains',
        'nombre__icontains',
        'apellido_paterno__icontains',
        'apellido_materno__icontains',
        'sexo__icontains',
        'rut_responsable_temporal__icontains',
        'comuna__nombre__icontains',
    ]

    def get_base_queryset(self):
        return Paciente.objects.filter(recien_nacido=True, status=True).order_by('apellido_paterno')

    def render_row(self, obj):
        apellidos = f"{obj.apellido_paterno or ''} {obj.apellido_materno or ''}".strip()

        ficha = Ficha.objects.filter(
            paciente=obj,
            establecimiento=self.request.user.establecimiento, status=True
        ).first()

        return {
            'ID': obj.id,
            'RUT': (obj.rut or '').upper(),
            'N° Ficha': (
                str(ficha.numero_ficha_sistema)
                if ficha and ficha.numero_ficha_sistema
                else 'SIN FICHA'
            ),
            'Nombre': (obj.nombre or '').upper(),
            'Apellidos': apellidos.upper(),
            'Fecha Nacimiento': (
                obj.fecha_nacimiento.strftime('%d/%m/%Y')
                if obj.fecha_nacimiento
                else '---'
            ),
            'Sexo': (obj.sexo or '').upper(),
            'Rut Responsable': (
                obj.rut_responsable_temporal.upper()
                if obj.rut_responsable_temporal
                   and obj.rut_responsable_temporal.lower() != 'nan'
                else 'SIN RUT'
            ),
            'Comuna': (getattr(obj.comuna, 'nombre', '') or '').upper(),
            'Observación': (
                ficha.observacion.upper()
                if ficha and ficha.observacion
                else 'SIN OBSERVACIÓN'
            ),
        }

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
        ficha = Ficha.objects.filter(paciente=obj, establecimiento=self.request.user.establecimiento,
                                     status=True).first()
        return {
            'ID': obj.id,
            'N° Ficha': (str(ficha.numero_ficha_sistema) if ficha and ficha.numero_ficha_sistema else 'SIN FICHA'),
            'Código': (obj.codigo or '').upper(),
            'RUT': (obj.rut or '').upper(),
            'Nombre': (obj.nombre or '').upper(),
            'NIP': (obj.nip or '').upper(),
            'Pasaporte': (obj.pasaporte or '').upper(),
            'Sexo': (obj.sexo or '').upper(),
            'Estado Civil': (obj.get_estado_civil_display() or '').upper(),
            'Comuna': (getattr(obj.comuna, 'nombre', '') or '').upper(),
            'Previsión': (getattr(obj.prevision, 'nombre', '') or '').upper(),
            'Observación': (ficha.observacion.lower() if ficha and ficha.observacion else 'SIN OBSERVACIÓN'),
        }

    def get_base_queryset(self):
        return Paciente.objects.filter(extranjero=True, status=True).order_by('nombre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Pacientes Extranjeros',
            'list_url': reverse_lazy('paciente_extranjero_list'),
            'export_csv_url': reverse_lazy('reports:export_paciente_extranjero_csv'),
            'datatable_enabled': True,
            'datatable_order': [[4, 'asc']],
            'datatable_page_length': 100,
            'columns': self.datatable_columns,
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
        ficha = Ficha.objects.filter(paciente=obj, establecimiento=self.request.user.establecimiento,
                                     status=True).first()
        return {
            'ID': obj.id,
            'N° Ficha': (str(ficha.numero_ficha_sistema) if ficha and ficha.numero_ficha_sistema else 'SIN FICHA'),
            'Código': (obj.codigo or '').upper(),
            'Nombre': (obj.nombre or '').upper(),
            'Sexo': (obj.sexo or '').upper(),
            'Rut Responsable': (
                obj.rut_madre.upper()
                if obj.rut_madre and obj.rut_madre.lower() != 'nan'
                else (
                    obj.rut_responsable_temporal.upper()
                    if obj.rut_responsable_temporal and obj.rut_responsable_temporal.lower() != 'nan'
                    else ''
                )
            ),
            'Comuna': (getattr(obj.comuna, 'nombre', '') or '').upper(),
            'Previsión': (getattr(obj.prevision, 'nombre', '') or '').upper(),
            'Observación': (ficha.observacion.lower() if ficha and ficha.observacion else 'SIN OBSERVACIÓN'),
        }

    def get_base_queryset(self):
        return Paciente.objects.filter(usar_rut_madre_como_responsable=True, status=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Pacientes que utilizan el rut de la madre como reponsable',
            'list_url': reverse_lazy('paciente_rut_madre_list'),
        })
        return context


class PacienteFallecidoListView(PacienteListView):
    datatable_columns = ['ID', 'N° Ficha', 'RUT', 'Nombre', 'Apellidos', 'Fecha Fallecimiento', 'Sexo', 'Estado Civil',
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
        return Paciente.objects.filter(fallecido=True, status=True)

    def render_row(self, obj):
        apellidos = f"{obj.apellido_paterno or ''} {obj.apellido_materno or ''}".strip()
        ficha = Ficha.objects.filter(paciente=obj, establecimiento=self.request.user.establecimiento,
                                     status=True).first()

        return {
            'ID': obj.id,
            'N° Ficha': (str(ficha.numero_ficha_sistema) if ficha and ficha.numero_ficha_sistema else 'SIN FICHA'),
            'RUT': (obj.rut or '').upper(),
            'Nombre': (obj.nombre or '').upper(),
            'Apellidos': apellidos.upper(),
            'Fecha Fallecimiento': obj.fecha_fallecimiento.strftime('%d/%m/%Y') if obj.fecha_fallecimiento else '---',
            'Sexo': (obj.sexo or '').upper(),
            'Estado Civil': (obj.get_estado_civil_display() or '').upper(),
            'Comuna': (getattr(obj.comuna, 'nombre', '') or '').upper(),
            'Observación': (ficha.observacion.lower() if ficha and ficha.observacion else 'SIN OBSERVACIÓN'),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Pacientes Fallecidos',
            'list_url': reverse_lazy('paciente_fallecido_list'),
            'export_csv_url': reverse_lazy('reports:export_paciente_fallecido_csv'),
        })
        return context


class PacientePuebloIndigenaListView(PacienteListView):
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

    def render_row(self, obj):
        ficha = Ficha.objects.filter(paciente=obj, establecimiento=self.request.user.establecimiento,
                                     status=True).first()
        nombre_completo = f"{(obj.nombre or '').upper()} {(obj.apellido_paterno or '').upper()} {(obj.apellido_materno or '').upper()}".strip()

        return {
            'ID': obj.id,
            'N° Ficha': (str(ficha.numero_ficha_sistema) if ficha and ficha.numero_ficha_sistema else 'SIN FICHA'),
            'RUT': obj.rut or 'Sin RUT',
            'Nombre': nombre_completo or 'Sin Nombre',
            'Sexo': obj.sexo or '',
            'Estado Civil': obj.get_estado_civil_display() or '',
            'Comuna': (getattr(obj.comuna, 'nombre', '') or '').upper(),
            'Observación': (ficha.observacion.lower() if ficha and ficha.observacion else 'SIN OBSERVACIÓN'),
        }

    def get_base_queryset(self):
        return Paciente.objects.filter(pueblo_indigena=True, status=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Pacientes Pertenecientes a Pueblos Indigenas',
            'list_url': reverse_lazy('paciente_pueblo_indigena_list'),
            'export_csv_url': reverse_lazy('reports:export_paciente_pueblo_indigena_csv'),
        })
        return context


class PacientesHistoryListView(GenericHistoryListView):
    base_model = Paciente
    permission_required = 'view_paciente'
    template_name = 'history/list.html'

    url_last_page = 'paciente_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_last_page'] = self.url_last_page
        return context


class PacienteFechaFormView(FormView):
    template_name = 'paciente/fecha_rango_form.html'
    form_class = PacienteFechaRangoForm
    permission_required = 'view_paciente'

    def get_success_url(self):
        return reverse_lazy('paciente_por_fecha_list')

    def form_valid(self, form):
        # Redirect with GET params for datatable view
        fecha_inicio = form.cleaned_data['fecha_inicio'].strftime('%Y-%m-%d')
        fecha_fin = form.cleaned_data['fecha_fin'].strftime('%Y-%m-%d')
        url = f"{self.get_success_url()}?fecha_inicio={fecha_inicio}&fecha_fin={fecha_fin}"
        return redirect(url)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Consultar por rango de fechas'
        return ctx


class PacientePorFechaListView(PacienteListView):

    def get_base_queryset(self):
        qs = Paciente.objects.filter(status=True)
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        if fecha_inicio and fecha_fin:
            fi = parse_date(fecha_inicio)
            ff = parse_date(fecha_fin)
            if fi and ff:
                from datetime import datetime, time
                start_dt = datetime.combine(fi, time.min)
                end_dt = datetime.combine(ff, time.max)
                qs = qs.filter(created_at__range=(start_dt, end_dt))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = PacienteFechaRangoForm(self.request.GET or None)
        context.update({
            'title': 'Pacientes por Rango de Fecha',
            'list_url': reverse_lazy('paciente_por_fecha_list'),
            'date_range_form': form,
        })
        return context


class PacienteDuplicadoListView(PacienteListView):
    template_name = 'paciente/list_duplicados.html'

    def get_base_queryset(self):
        ruts_duplicados = (
            Paciente.objects
            .filter(status=True)
            .values('rut')
            .annotate(total=Count('id'))
            .filter(total__gt=1)
            .values('rut')
        )

        return (
            Paciente.objects
            .filter(
                status=True,
                rut__in=Subquery(ruts_duplicados)
            )
            .order_by('rut', 'id')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Pacientes con RUT Duplicado',
            'list_url': reverse_lazy('paciente_list_duplicados'),
        })
        return context


class PacienteDeleteView(View):
    def post(self, request, pk, *args, **kwargs):
        paciente = get_object_or_404(Paciente, pk=pk)
        user = request.user

        # Verificar permisos (permisos totales == 2)
        if not (getattr(user, 'rol', None) and getattr(user.rol, 'paciente', None) == 2):
            messages.error(request, 'No tiene permisos para eliminar pacientes.')
            return redirect('ficha_paciente_manage')

        motivo = request.POST.get('motivo_eliminacion', 'Sin motivo especificado')

        try:
            with transaction.atomic():
                # 1. Buscar todas las fichas del paciente
                fichas = Ficha.objects.filter(paciente=paciente)

                for ficha in fichas:
                    # 1.1 Respaldar Movimientos de cada ficha
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
                            ficha=None,
                            servicio_clinico_destino=mov.servicio_clinico_destino,
                            estado=mov.estado,
                            usuario_eliminacion=user,
                            motivo_eliminacion=motivo,
                            created_by=user,
                            updated_by=request.user,
                        )
                        mov.delete()

                    # 1.2 Respaldar Ficha
                    RespaldoFicha.objects.create(
                        numero_ficha_sistema=ficha.numero_ficha_sistema,
                        numero_ficha_tarjeta=ficha.numero_ficha_tarjeta,
                        numero_ficha_respaldo=ficha.numero_ficha_respaldo,
                        rut=paciente.rut,
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
                        motivo_eliminacion=motivo,
                        created_by=user,
                        updated_by=request.user,
                    )
                    ficha.delete()

                # 2. Respaldar Paciente
                last_ficha = fichas.last()
                RespaldoPaciente.objects.create(
                    ficha=str(last_ficha.numero_ficha_sistema) if last_ficha else 'SIN FICHA',
                    codigo=paciente.codigo,
                    id_anterior=paciente.id_anterior,
                    rut=paciente.rut,
                    nip=paciente.nip,
                    nombre=paciente.nombre,
                    rut_madre=paciente.rut_madre,
                    apellido_paterno=paciente.apellido_paterno,
                    apellido_materno=paciente.apellido_materno,
                    pueblo_indigena=paciente.pueblo_indigena,
                    rut_responsable_temporal=paciente.rut_responsable_temporal,
                    usar_rut_madre_como_responsable=paciente.usar_rut_madre_como_responsable,
                    pasaporte=paciente.pasaporte,
                    nombre_social=paciente.nombre_social,
                    fecha_nacimiento=paciente.fecha_nacimiento,
                    sexo=paciente.sexo,
                    estado_civil=paciente.estado_civil,
                    nombres_padre=paciente.nombres_padre,
                    nombres_madre=paciente.nombres_madre,
                    nombre_pareja=paciente.nombre_pareja,
                    representante_legal=paciente.representante_legal,
                    direccion=paciente.direccion,
                    sin_telefono=paciente.sin_telefono,
                    numero_telefono1=paciente.numero_telefono1,
                    numero_telefono2=paciente.numero_telefono2,
                    ocupacion=paciente.ocupacion,
                    recien_nacido=paciente.recien_nacido,
                    extranjero=paciente.extranjero,
                    fallecido=paciente.fallecido,
                    fecha_fallecimiento=paciente.fecha_fallecimiento,
                    alergico_a=paciente.alergico_a,
                    comuna=paciente.comuna,
                    prevision=paciente.prevision,
                    genero=paciente.genero,
                    usuario=paciente.usuario,
                    usuario_anterior=paciente.usuario_anterior,
                    usuario_eliminacion=user,
                    motivo_eliminacion=motivo,
                    created_by=user,
                    updated_by=request.user,
                )

                # 3. Eliminar Paciente
                paciente.delete()

            messages.success(request, 'Paciente, sus fichas y movimientos respaldados y eliminados correctamente.')
        except Exception as e:
            messages.error(request, f'Error al eliminar el paciente: {str(e)}')

        return redirect('ficha_paciente_manage')
