# from django.contrib import messages
# from django.contrib.auth.mixins import PermissionRequiredMixin
# from django.http import HttpResponse
# from django.shortcuts import redirect
# from django.urls import reverse_lazy
# from django.utils.dateparse import parse_date
# from django.views.generic import DetailView, UpdateView
# from django.views.generic import TemplateView
# from django.views.generic.edit import FormView
#
# from core.history import GenericHistoryListView
# from kardex.forms.pacientes_fichas import PacienteForm
# from kardex.mixin import DataTableMixin
# from kardex.models import Ficha
# from kardex.models import Paciente
# from personas.forms.pacientes import FormPacienteActualizarRut, FormPacienteSinRut
# from personas.forms.pacientes import PacienteFechaRangoForm
#
# MODULE_NAME = 'Pacientes'
#
#
# class PacienteListView(PermissionRequiredMixin, DataTableMixin, TemplateView):
#     template_name = 'kardex/paciente/list.html'
#     model = Paciente
#     datatable_columns = ['ID', 'RUT', 'Nombre', 'Sexo', 'Estado Civil', 'Comuna', 'Previsión']
#     datatable_order_fields = [
#         'id',
#         None,
#         None,
#         'sexo',
#         'estado_civil',
#         'comuna__nombre',
#         'prevision__nombre'
#     ]
#
#     datatable_search_fields = [
#         'rut__icontains',
#         'nombre__icontains',
#         'apellido_paterno__icontains',
#         'apellido_materno__icontains',
#         'sexo__icontains',
#         'estado_civil__icontains',
#         'comuna__nombre__icontains',
#         'prevision__nombre__icontains'
#     ]
#
#     permission_view = 'kardex.view_paciente'
#
#     permission_required = 'kardex.view_paciente'
#     raise_exception = True
#
#     url_detail = 'kardex:paciente_detail'
#     url_update = 'kardex:paciente_update'
#
#     def get_base_queryset(self):
#         # Vista libre: no limitar por establecimiento, mostrar todos los pacientes
#         return Paciente.objects.filter(status='ACTIVE')
#
#     def render_row(self, obj):
#         nombre_completo = f"{(obj.nombre or '').upper()} {(obj.apellido_paterno or '').upper()} {(obj.apellido_materno or '').upper()}".strip()
#         return {
#             'ID': obj.id,
#             'RUT': obj.rut or 'Sin RUT',
#             'Nombre': nombre_completo or 'Sin Nombre',
#             'Sexo': obj.sexo or '',
#             'Estado Civil': obj.estado_civil or '',
#             'Comuna': (getattr(obj.comuna, 'nombre', '') or '').upper(),
#             'Previsión': (getattr(obj.prevision, 'nombre', '') or '').upper(),
#         }
#
#     def get(self, request, *args, **kwargs):
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatable'):
#             return self.get_datatable_response(request)
#         return super().get(request, *args, **kwargs)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context.update({
#             'title': 'Listado de Pacientes',
#             'list_url': reverse_lazy('kardex:paciente_list'),
#             'create_url': reverse_lazy('kardex:paciente_query'),
#             'datatable_enabled': True,
#             'datatable_order': [[0, 'desc']],
#             'datatable_page_length': 100,
#             'columns': self.datatable_columns,
#             'export_csv_url': reverse_lazy('reports:export_paciente_csv'),
#         })
#         return context
#
#
# class PacienteDetailView(PermissionRequiredMixin, DetailView):
#     model = Paciente
#     template_name = 'kardex/paciente/detail.html'
#     permission_required = 'kardex.view_paciente'
#     raise_exception = True
#
#     def render_to_response(self, context, **response_kwargs):
#         if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             from django.template.loader import render_to_string
#             html = render_to_string(self.template_name, context=context, request=self.request)
#             return HttpResponse(html)
#         return super().render_to_response(context, **response_kwargs)
#
#
# class PacienteActualizarRut(PermissionRequiredMixin, UpdateView):
#     template_name = 'kardex/paciente/form_rut.html'
#     model = Paciente
#     form_class = FormPacienteActualizarRut
#     success_url = reverse_lazy('kardex:paciente_list')
#     permission_required = 'kardex.change_paciente'
#     raise_exception = True
#
#     def form_valid(self, form):
#         # Guardar y responder acorde al tipo de solicitud
#         self.object = form.save()
#         if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             return JsonResponse({
#                 'success': True,
#                 'paciente_id': self.object.id,
#                 'rut': self.object.rut,
#                 'message': 'RUT del paciente actualizado correctamente.'
#             })
#         messages.success(self.request, 'RUT del paciente actualizado correctamente.')
#         return super().form_valid(form)
#
#     def form_invalid(self, form):
#         if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             return JsonResponse({'success': False, 'errors': form.errors}, status=400)
#         messages.error(self.request, 'Errores al actualizar el RUT del paciente.')
#         return super().form_invalid(form)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['title'] = 'Actualizar RUT del Paciente'
#         context['module_name'] = MODULE_NAME
#         context['list_url'] = self.success_url
#
#         paciente = self.object
#         # Construimos una lista de (label, valor) para mostrar en el panel derecho
#         fields_info = []
#         # Usar model_to_dict puede omitir ManyToMany; aquí listamos field por field para labels
#         for field in paciente._meta.fields:
#             try:
#                 label = getattr(paciente._meta.get_field(field.name), 'verbose_name', field.name)
#             except Exception:
#                 label = field.name
#             value = getattr(paciente, field.name, '')
#             # Formatear fechas
#             if hasattr(value, 'strftime'):
#                 try:
#                     value = value.strftime('%d/%m/%Y')
#                 except Exception:
#                     value = str(value)
#             # Resolver FKs a su string
#             if hasattr(value, '__class__') and value.__class__.__name__ == 'DeferredAttribute':
#                 value = getattr(paciente, field.name)
#             if field.related_model is not None:
#                 value = getattr(paciente, field.name)
#                 value = '' if value is None else str(value)
#             fields_info.append((str(label).capitalize(), '' if value is None else str(value)))
#         context['paciente_fields'] = fields_info
#         return context
#
#
# class PacienteRecienNacidoListView(PacienteListView):
#     datatable_columns = ['ID', 'Código', 'Nombre', 'Sexo', 'Rut Responsable', 'Comuna', 'Previsión']
#     datatable_order_fields = [
#         'id',
#         None,
#         None,
#         'codigo',
#         'nombre',
#         'sexo',
#         'rut_responsable_temporal',
#         'comuna__nombre',
#         'prevision__nombre'
#     ]
#
#     datatable_search_fields = [
#         'codigo__icontains',
#         'rut__icontains',
#         'nombre__icontains',
#         'apellido_paterno__icontains',
#         'apellido_materno__icontains',
#         'sexo__icontains',
#         'rut_responsable_temporal_icontains',
#         'comuna__nombre__icontains',
#         'prevision__nombre__icontains'
#     ]
#
#     def render_row(self, obj):
#         return {
#             'ID': obj.id,
#             'Código': obj.codigo.upper(),
#             'Nombre': obj.nombre.upper(),
#             'Sexo': obj.sexo.upper(),
#             'Rut Responsable': obj.rut_responsable_temporal if obj.rut_responsable_temporal == 'nan' else 'Sin RUT',
#             'Comuna': (getattr(obj.comuna, 'nombre', '') or '').upper(),
#             'Previsión': (getattr(obj.prevision, 'prevision', '') or '').upper(),
#         }
#
#     def get_base_queryset(self):
#         return Paciente.objects.filter(recien_nacido=True)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context.update({
#             'title': 'Pacientes Recién Nacidos',
#             'list_url': reverse_lazy('kardex:paciente_recien_nacido_list'),
#             'export_csv_url': reverse_lazy('reports:export_paciente_recien_nacido_csv'),
#         })
#         return context
#
#
# class PacienteExtranjeroListView(PacienteListView):
#     datatable_columns = ['ID', 'Código', 'RUT', 'Nombre', 'NIP', 'Pasaporte', 'Sexo', 'Estado Civil', 'Comuna',
#                          'Previsión']
#     datatable_order_fields = [
#         'id',
#         None,
#         None,
#         'codigo',
#         'rut',
#         'nombre',
#         'nip',
#         'pasaporte',
#         'sexo',
#         'estado_civil',
#         'comuna__nombre',
#         'prevision__nombre'
#     ]
#
#     datatable_search_fields = [
#         'codigo__icontains',
#         'rut__icontains',
#         'nombre__icontains',
#         'nip__icontains',
#         'pasaporte__icontains',
#         'apellido_paterno__icontains',
#         'apellido_materno__icontains',
#         'sexo__icontains',
#         'estado_civil__icontains',
#         'comuna__nombre__icontains',
#         'prevision__nombre__icontains'
#     ]
#
#     def render_row(self, obj):
#         return {
#             'ID': obj.id,
#             'Código': (obj.codigo or '').upper(),
#             'RUT': (obj.rut or '').upper(),
#             'Nombre': (obj.nombre or '').upper(),
#             'NIP': (obj.nip or '').upper(),
#             'Pasaporte': (obj.pasaporte or '').upper(),
#             'Sexo': (obj.sexo or '').upper(),
#             'Estado Civil': (obj.estado_civil or '').upper(),
#             'Comuna': (getattr(obj.comuna, 'nombre', '') or '').upper(),
#             'Previsión': (getattr(obj.prevision, 'nombre', '') or '').upper(),
#         }
#
#     def get_base_queryset(self):
#         return Paciente.objects.filter(extranjero=True)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context.update({
#             'title': 'Pacientes Extranjeros',
#             'list_url': reverse_lazy('kardex:paciente_extranjero_list'),
#             'export_csv_url': reverse_lazy('reports:export_paciente_extranjero_csv'),
#         })
#         return context
#
#
# class PacienteRutMadreListView(PacienteListView):
#     datatable_columns = ['ID', 'Código', 'Nombre', 'Sexo', 'Rut Responsable', 'Comuna', 'Previsión']
#     datatable_order_fields = [
#         'id',
#         None,
#         None,
#         'codigo',
#         'nombre',
#         'sexo',
#         'rut_responsable_temporal',
#         'comuna__nombre',
#         'prevision__nombre'
#     ]
#
#     datatable_search_fields = [
#         'codigo__icontains',
#         'rut__icontains',
#         'nombre__icontains',
#         'apellido_paterno__icontains',
#         'apellido_materno__icontains',
#         'sexo__icontains',
#         'rut_responsable_temporal_icontains',
#         'comuna__nombre__icontains',
#         'prevision__nombre__icontains'
#     ]
#
#     def render_row(self, obj):
#         return {
#             'ID': obj.id,
#             'Código': obj.codigo.upper(),
#             'Nombre': obj.nombre.upper(),
#             'Sexo': obj.sexo.upper(),
#             'Rut Responsable': obj.rut_responsable_temporal if obj.rut_responsable_temporal == 'nan' else 'Sin RUT',
#             'Comuna': (getattr(obj.comuna, 'nombre', '') or '').upper(),
#             'Previsión': (getattr(obj.prevision, 'prevision', '') or '').upper(),
#         }
#
#     def get_base_queryset(self):
#         return Paciente.objects.filter(usar_rut_madre_como_responsable=True)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context.update({
#             'title': 'Pacientes que utilizan el rut de la madre como reponsable',
#             'list_url': reverse_lazy('kardex:paciente_rut_madre_list'),
#         })
#         return context
#
#
# class PacienteFallecidoListView(PacienteListView):
#
#     def get_base_queryset(self):
#         return Paciente.objects.filter(fallecido=True)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context.update({
#             'title': 'Pacientes Fallecidos',
#             'list_url': reverse_lazy('kardex:paciente_fallecido_list'),
#             'export_csv_url': reverse_lazy('reports:export_paciente_fallecido_csv'),
#         })
#         return context
#
#
# class PacientePuebloIndigenaListView(PacienteListView):
#
#     def get_base_queryset(self):
#         return Paciente.objects.filter(pueblo_indigena=True)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context.update({
#             'title': 'Pacientes Pertenecientes a Pueblos Indigenas',
#             'list_url': reverse_lazy('kardex:paciente_pueblo_indigena_list'),
#             'export_csv_url': reverse_lazy('reports:export_paciente_pueblo_indigena_csv'),
#         })
#         return context
#
#
# class PacienteFechaFormView(PermissionRequiredMixin, FormView):
#     template_name = 'kardex/paciente/fecha_rango_form.html'
#     form_class = PacienteFechaRangoForm
#     permission_required = 'kardex.view_paciente'
#
#     def get_success_url(self):
#         return reverse_lazy('kardex:paciente_por_fecha_list')
#
#     def form_valid(self, form):
#         # Redirect with GET params for datatable view
#         fecha_inicio = form.cleaned_data['fecha_inicio'].strftime('%Y-%m-%d')
#         fecha_fin = form.cleaned_data['fecha_fin'].strftime('%Y-%m-%d')
#         url = f"{self.get_success_url()}?fecha_inicio={fecha_inicio}&fecha_fin={fecha_fin}"
#         return redirect(url)
#
#     def get_context_data(self, **kwargs):
#         ctx = super().get_context_data(**kwargs)
#         ctx['title'] = 'Consultar por rango de fechas'
#         return ctx
#
#
# class PacientePorFechaListView(PacienteListView):
#
#     def get_base_queryset(self):
#         qs = Paciente.objects.all()
#         fecha_inicio = self.request.GET.get('fecha_inicio')
#         fecha_fin = self.request.GET.get('fecha_fin')
#         if fecha_inicio and fecha_fin:
#             fi = parse_date(fecha_inicio)
#             ff = parse_date(fecha_fin)
#             if fi and ff:
#                 from datetime import datetime, time
#                 start_dt = datetime.combine(fi, time.min)
#                 end_dt = datetime.combine(ff, time.max)
#                 qs = qs.filter(created_at__range=(start_dt, end_dt))
#         return qs
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         form = PacienteFechaRangoForm(self.request.GET or None)
#         context.update({
#             'title': 'Pacientes por Rango de Fecha',
#             'list_url': reverse_lazy('kardex:paciente_por_fecha_list'),
#             'date_range_form': form,
#         })
#         return context
#
#
# # usuarios.py
# from django.http import JsonResponse
# from django.views.generic.edit import FormView
# from django.contrib.auth.mixins import PermissionRequiredMixin
#
#
# class PacienteQueryView(PermissionRequiredMixin, FormView):
#     template_name = 'kardex/paciente/form.html'
#     form_class = PacienteForm
#
#     # SOLO PARA ENTRAR A LA VISTA
#     permission_required = 'kardex.view_paciente'
#     raise_exception = True
#
#     success_url = reverse_lazy('kardex:paciente_query')
#
#     # --------------------------------------------------
#     # CONTEXTO
#     # --------------------------------------------------
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#
#         context['title'] = f'Formulario de Paciente {self.request.user.establecimiento.nombre}'
#
#         try:
#             if self.request.method == 'POST':
#                 context['debug_post'] = {
#                     k: self.request.POST.getlist(k)
#                     for k in self.request.POST.keys()
#                 }
#         except Exception:
#             context['debug_post'] = {}
#
#         return context
#
#     # --------------------------------------------------
#     # LOG POST
#     # --------------------------------------------------
#     def _log_post(self):
#         try:
#             print("===== POST DATA (PacienteQueryView) =====")
#             for k in self.request.POST.keys():
#                 vals = self.request.POST.getlist(k)
#                 print(f"{k}: {vals}")
#             print("=========================================")
#         except Exception as e:
#             print(f"[WARN] No se pudo loguear POST: {e}")
#
#     # --------------------------------------------------
#     # RESPUESTA DE PERMISOS
#     # --------------------------------------------------
#     def _forbidden(self, mensaje):
#         if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             return JsonResponse({'success': False, 'error': mensaje}, status=403)
#
#         raise PermissionDenied(mensaje)
#
#     # --------------------------------------------------
#     # FORM VALID
#     # --------------------------------------------------
#     def form_valid(self, form):
#
#         self._log_post()
#
#         try:
#             datos = form.cleaned_data
#
#             # --------------------------------------------
#             # BUSCAR O CREAR PACIENTE
#             # --------------------------------------------
#             rut = datos.get('rut')
#             paciente = Paciente.objects.filter(rut=rut).first()
#
#             creating = False
#             if not paciente:
#                 creating = True
#
#             # --------------------------------------------
#             # VALIDACIÓN DE PERMISOS
#             # --------------------------------------------
#             if creating:
#                 if not self.request.user.has_perm('kardex.add_paciente'):
#                     return self._forbidden("No tienes permiso para crear pacientes.")
#             else:
#                 if not self.request.user.has_perm('kardex.change_paciente'):
#                     return self._forbidden("No tienes permiso para modificar pacientes.")
#
#             # --------------------------------------------
#             # ASIGNAR / ACTUALIZAR PACIENTE
#             # --------------------------------------------
#             if creating:
#                 paciente = Paciente(rut=rut)
#
#             ATTRS = [
#                 'nombre', 'apellido_paterno', 'apellido_materno', 'nombre_social', 'genero',
#                 'fecha_nacimiento', 'sexo', 'estado_civil', 'rut_madre', 'nombres_madre', 'nombres_padre',
#                 'nombre_pareja', 'representante_legal', 'pueblo_indigena', 'recien_nacido',
#                 'extranjero', 'fallecido', 'fecha_fallecimiento', 'alergico_a', 'direccion',
#                 'sin_telefono', 'numero_telefono1', 'numero_telefono2', 'ocupacion', 'pasaporte',
#                 'rut_responsable_temporal', 'usar_rut_madre_como_responsable',
#             ]
#
#             for attr in ATTRS:
#                 if attr in datos:
#                     setattr(paciente, attr, datos.get(attr))
#
#             # Relaciones
#             paciente.comuna = datos.get('comuna')
#             paciente.prevision = datos.get('prevision')
#             paciente.usuario = getattr(self.request, 'user', None)
#
#             paciente.save()
#
#             # --------------------------------------------
#             # FICHA
#             # --------------------------------------------
#             numero_ficha_sistema = None
#
#             try:
#                 establecimiento = self.request.user.establecimiento
#             except Exception:
#                 establecimiento = None
#
#             sector = datos.get('sector')
#             observacion = datos.get('observacion')
#
#             if establecimiento:
#                 ficha = Ficha.objects.filter(
#                     paciente=paciente,
#                     establecimiento=establecimiento
#                 ).first()
#
#                 if not ficha:
#                     ficha = Ficha(
#                         paciente=paciente,
#                         establecimiento=establecimiento,
#                         usuario=self.request.user
#                     )
#
#                 if sector:
#                     ficha.sector = sector
#
#                 if observacion:
#                     ficha.observacion = observacion
#
#                 ficha.save()
#                 numero_ficha_sistema = ficha.numero_ficha_sistema
#
#             # --------------------------------------------
#             # RESPUESTA AJAX
#             # --------------------------------------------
#             if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#                 return JsonResponse({
#                     'success': True,
#                     'message': (
#                         'Paciente creado correctamente'
#                         if creating else
#                         'Paciente actualizado correctamente'
#                     ),
#                     'paciente_id': paciente.id,
#                     'numero_ficha_sistema': numero_ficha_sistema
#                 })
#
#             # --------------------------------------------
#             # RESPUESTA NORMAL
#             # --------------------------------------------
#             messages.success(
#                 self.request,
#                 'Paciente creado correctamente.' if creating
#                 else 'Paciente actualizado correctamente.'
#             )
#
#             return super().form_valid(form)
#
#         # --------------------------------------------
#         # ERRORES GENERALES
#         # --------------------------------------------
#         except Exception as e:
#             if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#                 return JsonResponse({'success': False, 'error': str(e)}, status=400)
#
#             messages.error(self.request, f'Error al guardar: {str(e)}')
#             return self.form_invalid(form)
#
#     # --------------------------------------------------
#     # FORM INVALID
#     # --------------------------------------------------
#     def form_invalid(self, form):
#
#         self._log_post()
#
#         if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             errors = {}
#             for field, error_list in form.errors.items():
#                 errors[field] = error_list
#                 print(f"Error en {field}: {error_list}")
#
#             return JsonResponse({'success': False, 'errors': errors}, status=400)
#
#         messages.error(self.request, 'Por favor corrija los errores en el formulario.')
#         return super().form_invalid(form)
#
#
# class PacienteCreateSinRutView(PermissionRequiredMixin, FormView):
#     template_name = 'kardex/paciente/sin_rut.html'
#     form_class = FormPacienteSinRut
#     permission_required = 'kardex.add_paciente'
#     raise_exception = True
#
#     def form_valid(self, form):
#         paciente = form.save(commit=False)
#         try:
#             paciente.usuario = getattr(self.request, 'user', None)
#         except Exception:
#             pass
#         paciente.save()
#
#         # Crear ficha automáticamente usando el establecimiento del usuario
#         try:
#             establecimiento = getattr(self.request.user, 'establecimiento', None)
#         except Exception:
#             establecimiento = None
#
#         if establecimiento:
#             ficha = Ficha(
#                 paciente=paciente,
#                 establecimiento=establecimiento,
#                 usuario=getattr(self.request, 'user', None),
#                 sector=form.cleaned_data.get('sector')
#             )
#             ficha.save()
#
#         messages.success(self.request, 'Paciente creado y ficha asociada correctamente.')
#         from django.shortcuts import redirect
#         from django.urls import reverse
#         return redirect(reverse('kardex:paciente_detail', kwargs={'pk': paciente.pk}))
#
#     def form_invalid(self, form):
#         messages.error(self.request, 'Por favor corrija los errores en el formulario.')
#         return super().form_invalid(form)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         hay_ficha = None
#
#         # Obtener el próximo número de ficha
#         try:
#             establecimiento = getattr(self.request.user, 'establecimiento', None)
#
#             if establecimiento:
#                 # Obtener el máximo número de ficha para este establecimiento
#                 from django.db.models import Max
#                 max_ficha = Ficha.objects.filter(
#                     establecimiento=establecimiento
#                 ).aggregate(
#                     max_numero=Max('numero_ficha_sistema')
#                 )
#
#                 siguiente_numero = (max_ficha['max_numero'] or 0) + 1
#                 context['siguiente_numero_ficha'] = siguiente_numero
#             else:
#                 context['siguiente_numero_ficha'] = "No disponible"
#
#         except Exception as e:
#             context['siguiente_numero_ficha'] = "No disponible"
#
#         # ===================
#         # CODIGO PACIENTE
#         # ===================
#
#         try:
#             ultimo_paciente = Paciente.objects.order_by('-id').first()
#
#             if ultimo_paciente and ultimo_paciente.codigo:
#
#                 # Eliminar all excepto números
#                 import re
#                 numero = int(re.sub(r'\D', '', ultimo_paciente.codigo))
#
#                 nuevo_codigo = f"PAC-{numero + 1:06d}"
#
#             else:
#                 nuevo_codigo = "PAC-000001"
#
#             context['codigo_paciente_preview'] = nuevo_codigo
#
#         except:
#             context['codigo_paciente_preview'] = "PAC-000001"
#
#         context['title'] = f'Formulario de Paciente Sin Rut'
#         return context
#
#
# class PacientesHistoryListView(GenericHistoryListView):
#     base_model = Paciente
#     permission_required = 'kardex.view_paciente'
#     template_name = 'kardex/history/list.html'
