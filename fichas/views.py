from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from clinica.models import Ficha
from personas.models.pacientes import Paciente
from .forms import PacienteForm, FichaForm

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
        Guarda ambos formularios en una sola operación:
        - create/create
        - update/create
        - update/update
        """
        self.paciente = self.get_paciente_from_post()
        self.ficha = self.get_ficha_from_post()

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
        1) Si viene numero_ficha -> buscamos ficha y su paciente (filtrado por establecimiento y status=True)
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
                status=True
            ).first()

            if ficha:
                return ficha.paciente, ficha
            else:
                messages.warning(self.request, 'No se encontró una ficha activa con ese número en su establecimiento.')
                return None, None

        if rut:
            paciente = Paciente.objects.filter(rut=rut).first()
            if paciente:
                # Si encontramos al paciente, buscamos si tiene ficha en este establecimiento
                ficha = Ficha.objects.filter(
                    paciente=paciente,
                    establecimiento=establecimiento,
                    status=True
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
            return Paciente.objects.filter(rut=rut).first()

        return None

    def get_ficha_from_post(self):
        """
        Al guardar NO dependemos del GET.
        Intentamos por:
        1) ficha_id hidden
        2) numero_ficha del formulario
        """
        establecimiento = getattr(self.request.user, 'establecimiento', None)
        ficha_id = self.request.POST.get('ficha_id')

        if ficha_id:
            ficha = Ficha.objects.select_related('paciente').filter(pk=ficha_id, status=True).first()
            if ficha:
                return ficha

        numero_ficha = self.request.POST.get('ficha-numero_ficha_sistema', '').strip()
        if numero_ficha:
            return Ficha.objects.select_related('paciente').filter(
                numero_ficha_sistema=numero_ficha,
                establecimiento=establecimiento,
                status=True
            ).first()

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

        # Si la ficha ya existe y pertenece a otro paciente, no permitimos cruzar datos
        if ficha.pk and ficha.paciente_id and ficha.paciente_id != paciente.id:
            raise ValidationError('La ficha encontrada pertenece a otro paciente y no puede reasignarse.')

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
