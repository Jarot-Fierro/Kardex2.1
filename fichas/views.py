import csv

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, ProtectedError
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, TemplateView

from clinica.models import Ficha
from clinica.models.movimiento_ficha import MovimientoFicha
from core.validations import format_rut, validate_rut
from geografia.models.comuna import Comuna
from personas.models.pacientes import Paciente
from .forms import FusionarPacientesForm, PacienteForm, FichaForm
from .services import fusionar_pacientes_clinicos


class FusionarPacientesView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    template_name = 'fichas/fusionar_pacientes.html'
    form_class = FusionarPacientesForm
    permission_required = 'personas.change_paciente'  # O el permiso que definas

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        ficticio_id = self.request.GET.get('ficticio', '').strip()
        real_id = self.request.GET.get('real', '').strip()
        if ficticio_id:
            kwargs['paciente_ficticio'] = get_object_or_404(Paciente, pk=ficticio_id)
        if real_id:
            kwargs['paciente_real'] = get_object_or_404(Paciente, pk=real_id)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ficticio_id = self.request.GET.get('ficticio', '').strip()
        real_id = self.request.GET.get('real', '').strip()
        q_ficticio = self.request.GET.get('q_ficticio', '')
        q_real = self.request.GET.get('q_real', '')
        user_est = self.request.user.establecimiento

        context['title'] = f'Fusionar Pacientes | {self.request.user.establecimiento}'

        # Búsqueda de pacientes ficticios filtrada por establecimiento y que estén activos
        if q_ficticio:
            if validate_rut(q_ficticio):
                q_ficticio = format_rut(q_ficticio)

            # Filtrar por establecimiento a través de la ficha del paciente
            base_qs = Paciente.objects.filter(fichas_pacientes__establecimiento=user_est, )

            # Restringir la búsqueda a RUT o Número de Ficha
            context['resultados_ficticio'] = base_qs.filter(
                Q(rut__icontains=q_ficticio) |
                Q(fichas_pacientes__numero_ficha_sistema__icontains=q_ficticio)
            ).distinct()[:10]
            context['q_ficticio'] = q_ficticio

        # Búsqueda de pacientes reales filtrada por establecimiento y que estén activos
        if q_real:
            if validate_rut(q_real):
                q_real = format_rut(q_real)

            # Filtrar por establecimiento a través de la ficha del paciente
            base_qs = Paciente.objects.filter(fichas_pacientes__establecimiento=user_est, )

            # Restringir la búsqueda a RUT o Número de Ficha
            context['resultados_real'] = base_qs.filter(
                Q(rut__icontains=q_real) |
                Q(fichas_pacientes__numero_ficha_sistema__icontains=q_real)
            ).distinct()[:10]
            context['q_real'] = q_real

        if ficticio_id:
            ficticio = get_object_or_404(Paciente, pk=ficticio_id)
            context['paciente_ficticio'] = ficticio
            # Ficha filtrada por establecimiento
            ficha_ficticia_qs = Ficha.objects.filter(paciente=ficticio)
            if user_est:
                ficha_ficticia_qs = ficha_ficticia_qs.filter(establecimiento=user_est)

            context['ficha_ficticia'] = ficha_ficticia_qs.first()
            if context['ficha_ficticia']:
                context['movimientos_ficticio'] = MovimientoFicha.objects.filter(ficha=context['ficha_ficticia'])

        if real_id:
            real = get_object_or_404(Paciente, pk=real_id)
            context['paciente_real'] = real
            # Ficha filtrada por establecimiento
            ficha_real_qs = Ficha.objects.filter(paciente=real)
            if user_est:
                ficha_real_qs = ficha_real_qs.filter(establecimiento=user_est)

            context['ficha_real'] = ficha_real_qs.first()
            if context['ficha_real']:
                context['movimientos_real'] = MovimientoFicha.objects.filter(ficha=context['ficha_real'])

        return context

    def post(self, request, *args, **kwargs):
        # print("DEBUG: FusionarPacientesView.post iniciado")
        # print(f"DEBUG: POST data: {request.POST}")
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        # print("DEBUG: form_invalid llamado")
        # print(f"DEBUG: Form errors: {form.errors}")
        return super().form_invalid(form)

    def form_valid(self, form):
        # print("DEBUG: form_valid iniciado")
        paciente_ficticio = form.cleaned_data['paciente_ficticio']
        paciente_real = form.cleaned_data['paciente_real']
        ficha_conservar_choice = form.cleaned_data['ficha_a_conservar']
        borrar_paciente_ficticio = form.cleaned_data['borrar_paciente']
        motivo = form.cleaned_data['motivo']

        user_est = self.request.user.establecimiento
        ficha_ficticia = Ficha.objects.filter(paciente=paciente_ficticio, establecimiento=user_est).first()
        ficha_real = Ficha.objects.filter(paciente=paciente_real, establecimiento=user_est).first()

        if ficha_conservar_choice == 'ficticia':
            ficha_a_conservar = ficha_ficticia
            ficha_a_eliminar = ficha_real
        else:
            ficha_a_conservar = ficha_real
            ficha_a_eliminar = ficha_ficticia

        if not ficha_a_conservar:
            messages.error(self.request, "La ficha a conservar no existe en su establecimiento.")
            return self.form_invalid(form)

        # Obtener todos los movimientos del paciente ficticio y real (todas sus fichas)
        movimientos_ficticio_ids = list(MovimientoFicha.objects.filter(ficha__paciente=paciente_ficticio).values_list('id', flat=True))
        movimientos_real_ids = list(MovimientoFicha.objects.filter(ficha__paciente=paciente_real).values_list('id', flat=True))

        try:
            fusionar_pacientes_clinicos(
                paciente_ficticio=paciente_ficticio,
                paciente_real=paciente_real,
                ficha_a_conservar=ficha_a_conservar,
                ficha_a_eliminar=ficha_a_eliminar,
                movimientos_ficticio_ids=movimientos_ficticio_ids,
                movimientos_real_ids=movimientos_real_ids,
                usuario=self.request.user,
                motivo_fusion=motivo,
                borrar_paciente_ficticio=borrar_paciente_ficticio
            )
            messages.success(self.request, "La fusión de pacientes se realizó correctamente.")
            return redirect('ficha_paciente_manage')
        except ProtectedError as e:
            # Extraer objetos protegidos para listarlos
            protected_objects = []
            from clinica.models.movimiento_ficha_monologo_controlado import MovimientoMonologoControlado

            for obj in e.protected_objects:
                if isinstance(obj, Ficha):
                    protected_objects.append({
                        'tipo': 'Ficha',
                        'detalle': f"Ficha #{obj.numero_ficha_sistema}",
                        'rut': obj.paciente.rut if obj.paciente else 'S/R',
                        'nombre': obj.paciente.nombre_completo if obj.paciente else 'S/N',
                        'establecimiento': obj.establecimiento.nombre if obj.establecimiento else 'N/A'
                    })
                elif isinstance(obj, MovimientoMonologoControlado):
                    protected_objects.append({
                        'tipo': 'Movimiento Monólogo',
                        'detalle': f"Movimiento en {obj.establecimiento.nombre if obj.establecimiento else 'N/A'}",
                        'rut': obj.rut_paciente.rut if obj.rut_paciente else obj.rut,
                        'nombre': obj.rut_paciente.nombre_completo if obj.rut_paciente else 'S/N',
                        'establecimiento': obj.establecimiento.nombre if obj.establecimiento else 'N/A'
                    })
                else:
                    protected_objects.append({
                        'tipo': type(obj).__name__,
                        'detalle': str(obj),
                        'rut': 'N/A',
                        'nombre': 'N/A',
                        'establecimiento': 'N/A'
                    })

            context = self.get_context_data(form=form)
            context['protected_objects'] = protected_objects
            messages.error(self.request, "No se puede completar la fusión porque existen registros protegidos en otros establecimientos.")
            return self.render_to_response(context)
        except Exception as e:
            print(f"DEBUG: Error en fusión: {e}")
            messages.error(self.request, f"Error al procesar la fusión: {str(e)}")
            return self.form_invalid(form)


class PacienteAutocompleteView(View):
    def get(self, request, *args, **kwargs):
        term = request.GET.get('term', '').strip()
        user_est = self.request.user.establecimiento
        if not term:
            return JsonResponse({'results': []})

        if validate_rut(term):
            term = format_rut(term)

        # Filtrar pacientes por RUT o Ficha y por establecimiento
        base_qs = Paciente.objects.all()
        if user_est:
            base_qs = base_qs.filter(fichas_pacientes__establecimiento=user_est)

        pacientes = base_qs.filter(
            Q(rut__icontains=term) |
            Q(fichas_pacientes__numero_ficha_sistema__icontains=term)
        ).distinct()[:20]  # Limitar resultados para velocidad

        results = [
            {'id': p.id, 'text': f"{p.rut or 'S/R'} - {p.nombre_completo}"}
            for p in pacientes
        ]
        return JsonResponse({'results': results})


MODULE_NAME = 'Paciente / Ficha'


class PacienteFichaManageView(TemplateView):
    template_name = 'fichas/form.html'
    success_url = reverse_lazy('ficha_paciente_manage')

    def dispatch(self, request, *args, **kwargs):
        self.paciente = None
        self.ficha = None
        return super().dispatch(request, *args, **kwargs)

    # =========================================================
    # GET PRINCIPAL
    # =========================================================
    def get(self, request, *args, **kwargs):
        """
        GET inicial o GET por búsqueda:
        - ?rut=...
        - ?numero_ficha=...
        """
        self.paciente, self.ficha = self.resolve_instances_from_get()

        if self.ficha:
            messages.info(
                request,
                'Se encontró una ficha existente y se cargaron sus datos junto al paciente.'
            )
        elif self.paciente:
            messages.info(
                request,
                'Se encontró un paciente existente. Puede completar y crear una nueva ficha.'
            )

        paciente_form, ficha_form = self.get_forms(
            paciente=self.paciente,
            ficha=self.ficha
        )

        context = self.get_context_data(
            paciente_form=paciente_form,
            ficha_form=ficha_form,
            paciente_obj=self.paciente,
            ficha_obj=self.ficha,
        )
        return self.render_to_response(context)

    # =========================================================
    # POST GUARDAR
    # =========================================================
    def post(self, request, *args, **kwargs):
        """
        Guarda ambos formularios en una sola operación o maneja eliminación.
        """
        self.paciente = self.get_paciente_from_post()
        self.ficha = self.get_ficha_from_post()

        action = request.POST.get('action')

        if action == 'eliminar_ficha':
            if self.ficha:
                return redirect('ficha_delete', pk=self.ficha.pk)
            return redirect('ficha_paciente_manage')

        if action == 'eliminar_paciente_ficha':
            if self.paciente:
                return redirect('paciente_delete', pk=self.paciente.pk)
            return redirect('ficha_paciente_manage')

        paciente_form, ficha_form = self.get_forms(
            paciente=self.paciente,
            ficha=self.ficha,
            post_data=request.POST
        )

        if not paciente_form.is_valid() or not ficha_form.is_valid():
            return self.form_invalid(paciente_form, ficha_form)

        return self.form_valid(paciente_form, ficha_form)

    # =========================================================
    # FORM VALID / INVALID (estilo similar al tuyo)
    # =========================================================
    def form_valid(self, paciente_form, ficha_form):
        try:
            with transaction.atomic():
                paciente_guardado, paciente_creado = self.save_paciente(paciente_form)
                ficha_guardada, ficha_creada = self.save_ficha(ficha_form, paciente_guardado)

                # Mensaje según escenario
                if paciente_creado and ficha_creada:
                    messages.success(self.request, 'Paciente y ficha creados correctamente.')
                elif not paciente_creado and ficha_creada:
                    messages.success(self.request, 'Paciente actualizado y ficha creada correctamente.')
                elif not paciente_creado and not ficha_creada:
                    messages.info(self.request, 'Paciente y ficha actualizados correctamente.')
                else:
                    messages.success(self.request, 'Registro guardado correctamente.')

                # Redirigimos a la misma vista para dejar la página "cargada"
                return redirect(f'{self.success_url}?numero_ficha={ficha_guardada.numero_ficha_sistema}')

        except ValidationError as e:
            messages.error(self.request, str(e))
        except Exception as e:
            messages.error(self.request, f'Ocurrió un error al guardar: {str(e)}')

        return self.form_invalid(paciente_form, ficha_form)

    def form_invalid(self, paciente_form, ficha_form):
        messages.error(self.request, 'Hay errores en el formulario.')

        context = self.get_context_data(
            paciente_form=paciente_form,
            ficha_form=ficha_form,
            paciente_obj=self.paciente,
            ficha_obj=self.ficha,
        )
        return self.render_to_response(context)

    # =========================================================
    # RESOLVER INSTANCIAS DESDE GET (BUSCADORES)
    # =========================================================
    def resolve_instances_from_get(self):
        """
        Prioridad:
        1) Si viene numero_ficha -> buscamos ficha y su paciente (filtrado por establecimiento y )
        2) Si no, si viene rut -> buscamos paciente y su ficha en el establecimiento actual
        """
        numero_ficha = self.request.GET.get('numero_ficha', '').strip()
        rut = self.request.GET.get('rut', '').strip()
        establecimiento = getattr(self.request.user, 'establecimiento', None)

        if numero_ficha:
            # Filtramos por numero, establecimiento y status activo
            ficha = Ficha.objects.select_related('paciente').filter(
                numero_ficha_sistema=numero_ficha,
                establecimiento=establecimiento,
                
            ).first()

            if ficha:
                return ficha.paciente, ficha
            else:
                messages.warning(self.request, 'No se encontró una ficha activa con ese número en su establecimiento.')
                return None, None

        if rut:
            if validate_rut(rut):
                rut = format_rut(rut)

            paciente = Paciente.objects.filter(rut=rut).first()
            if paciente:
                # Si encontramos al paciente, buscamos si tiene ficha en este establecimiento
                ficha = Ficha.objects.filter(
                    paciente=paciente,
                    establecimiento=establecimiento,
                    
                ).first()
                return paciente, ficha
            else:
                messages.warning(self.request, 'No se encontró un paciente con ese RUT.')
                return None, None

        return None, None

    # =========================================================
    # RECUPERAR INSTANCIAS DESDE POST (IMPORTANTE)
    # =========================================================
    def get_paciente_from_post(self):
        """
        Al guardar NO dependemos del GET.
        Intentamos por:
        1) paciente_id hidden
        2) rut del formulario
        """
        paciente_id = self.request.POST.get('paciente_id')
        if paciente_id:
            paciente = Paciente.objects.filter(pk=paciente_id).first()
            if paciente:
                return paciente

        rut = self.request.POST.get('paciente-rut', '').strip()
        if rut:
            if validate_rut(rut):
                rut = format_rut(rut)
            return Paciente.objects.filter(rut=rut).first()

        return None

    def get_ficha_from_post(self):
        """
        Al guardar NO dependemos del GET.
        Solo usamos ficha_id (hidden) para determinar si se está editando una ficha existente.
        NUNCA buscamos por numero_ficha_sistema aquí para evitar reasignaciones accidentales.
        """
        ficha_id = self.request.POST.get('ficha_id')

        if ficha_id:
            ficha = Ficha.objects.select_related('paciente').filter(pk=ficha_id).first()
            if ficha:
                return ficha

        return None

    # =========================================================
    # CONSTRUCCIÓN DE FORMULARIOS
    # =========================================================
    def get_forms(self, paciente=None, ficha=None, post_data=None):
        """
        Devuelve ambos formularios con prefix para evitar conflictos.
        """
        kwargs_ficha = {'instance': ficha, 'prefix': 'ficha'}
        establecimiento = getattr(self.request.user, 'establecimiento', None)
        if establecimiento:
            kwargs_ficha['establecimiento'] = establecimiento

        if post_data:
            paciente_form = PacienteForm(
                post_data,
                instance=paciente,
                prefix='paciente'
            )
            ficha_form = FichaForm(
                post_data,
                **kwargs_ficha
            )
        else:
            paciente_form = PacienteForm(
                instance=paciente,
                prefix='paciente'
            )
            ficha_form = FichaForm(
                **kwargs_ficha
            )

        return paciente_form, ficha_form

    # =========================================================
    # GUARDADO DE PACIENTE
    # =========================================================
    def save_paciente(self, paciente_form):
        """
        Guarda paciente con create/update inteligente.
        """
        paciente = paciente_form.save(commit=False)
        creado = paciente.pk is None

        # Auditoría opcional (si tus modelos tienen estos campos)
        if hasattr(paciente, 'created_by') and creado:
            paciente.created_by = self.request.user

        if hasattr(paciente, 'updated_by'):
            paciente.updated_by = self.request.user

        paciente.save()

        return paciente, creado

    # =========================================================
    # GUARDADO DE FICHA
    # =========================================================
    def save_ficha(self, ficha_form, paciente):
        """
        Guarda ficha asociándola al paciente y al establecimiento del usuario.
        """
        ficha = ficha_form.save(commit=False)
        creada = ficha.pk is None

        # Doble verificación de seguridad:
        # Si la ficha ya existe, verificamos que pertenezca al mismo paciente que estamos procesando.
        if not creada and ficha.paciente_id and ficha.paciente_id != paciente.id:
            raise ValidationError(
                f"Seguridad: Esta ficha (ID {ficha.pk}) pertenece al paciente con ID {ficha.paciente_id} "
                f"y no puede ser reasignada al paciente con ID {paciente.id}."
            )

        # Asignar paciente
        ficha.paciente = paciente

        # Asignar establecimiento si es nueva
        if creada:
            establecimiento = getattr(self.request.user, 'establecimiento', None)
            if establecimiento:
                ficha.establecimiento = establecimiento
            ficha.status = True  # Aseguramos status True al crear

        # Auditoría opcional
        if hasattr(ficha, 'created_by') and creada:
            ficha.created_by = self.request.user

        if hasattr(ficha, 'updated_by'):
            ficha.updated_by = self.request.user

        ficha.save()

        return ficha, creada

    # =========================================================
    # CONTEXTO
    # =========================================================
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        paciente_obj = kwargs.get('paciente_obj')
        ficha_obj = kwargs.get('ficha_obj')

        context['title'] = f'Gestión de Paciente y Ficha {self.request.user.establecimiento}'
        context['list_url'] = self.success_url
        context['module_name'] = MODULE_NAME

        context['paciente_form'] = kwargs.get('paciente_form')
        context['ficha_form'] = kwargs.get('ficha_form')

        context['paciente_exists'] = paciente_obj is not None
        context['ficha_exists'] = ficha_obj is not None

        # action visual, similar a tu estructura
        if ficha_obj:
            context['action'] = 'edit'
        elif paciente_obj:
            context['action'] = 'partial'
        else:
            context['action'] = 'add'

        return context




def paciente_list_v2(request):
    user_est = request.user.establecimiento
    pacientes_list = Paciente.objects.all().order_by('apellido_paterno', 'apellido_materno', 'nombre')

    rut = request.GET.get('rut', '').strip()
    nombres = request.GET.get('nombres', '').strip()
    apellido_paterno = request.GET.get('apellido_paterno', '').strip()
    apellido_materno = request.GET.get('apellido_materno', '').strip()
    comuna_id = request.GET.get('comuna')
    sexo = request.GET.get('sexo')
    correlativo = request.GET.get('correlativo', '').strip()

    if rut:
        pacientes_list = pacientes_list.filter(rut__icontains=rut)
    if nombres:
        pacientes_list = pacientes_list.filter(nombre__icontains=nombres)
    if apellido_paterno:
        pacientes_list = pacientes_list.filter(apellido_paterno__icontains=apellido_paterno)
    if apellido_materno:
        pacientes_list = pacientes_list.filter(apellido_materno__icontains=apellido_materno)
    if comuna_id:
        pacientes_list = pacientes_list.filter(comuna_id=comuna_id)
    if sexo:
        pacientes_list = pacientes_list.filter(sexo=sexo)
    if correlativo:
        pacientes_list = pacientes_list.filter(
            fichas_pacientes__numero_ficha_sistema__icontains=correlativo,
            fichas_pacientes__establecimiento=user_est
        ).distinct()

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="pacientes.csv"'
        response.write('\ufeff'.encode('utf-8'))
        writer = csv.writer(response)
        writer.writerow(['RUT', 'Nombres', 'Apellidos', 'Comuna', 'Sexo', 'Ficha (Establecimiento)'])
        for p in pacientes_list:
            ficha = p.fichas_pacientes.filter(establecimiento=user_est).first()
            num_ficha = ficha.numero_ficha_sistema if ficha else "S/F"
            writer.writerow([
                p.rut,
                p.nombre,
                f"{p.apellido_paterno} {p.apellido_materno}",
                p.comuna.nombre if p.comuna else "",
                p.get_sexo_display(),
                num_ficha
            ])
        return response

    paginator = Paginator(pacientes_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    comunas = Comuna.objects.all()
    from core.choices import SEXO_CHOICES

    context = {
        'page_obj': page_obj,
        'comunas': comunas,
        'sexo_choices': SEXO_CHOICES,
        'title': 'Búsqueda de Pacientes'
    }

    return render(request, 'fichas/list_paciente_v2.html', context)