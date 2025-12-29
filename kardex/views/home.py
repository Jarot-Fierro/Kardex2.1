from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from kardex.models import Paciente, Ficha


class HomeDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get(self, request, *args, **kwargs):
        # Quick search: by RUT exact or name contains
        q = request.GET.get('q')
        if q:
            qs = Paciente.objects.filter(status='ACTIVE').filter(
                Q(rut__iexact=q) |
                Q(nombre__icontains=q) |
                Q(apellido_paterno__icontains=q) |
                Q(apellido_materno__icontains=q)
            )

            if qs.count() == 1:
                paciente = qs.first()
                return redirect('kardex:paciente_detail', pk=paciente.pk)
            elif qs.count() == 0:
                messages.warning(request, 'No se encontraron pacientes para la búsqueda ingresada.')
            else:
                messages.info(request, 'Se encontraron múltiples pacientes. Por favor refina tu búsqueda.')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        establecimiento = getattr(user, 'establecimiento', None)

        # User context
        rol = None
        if user.is_authenticated:
            # Prefer group name as role if present
            first_group = user.groups.first()
            rol = first_group.name if first_group else getattr(user, 'tipo_perfil', None)

        # Summary cards
        total_pacientes = Paciente.objects.count()

        # Fichas directamente relacionadas al paciente (ya no hay tabla de ingresos)
        fichas_qs = Ficha.objects.select_related('paciente', 'establecimiento')
        if establecimiento is not None:
            fichas_qs = fichas_qs.filter(establecimiento=establecimiento, paciente__status='ACTIVE')

        # Para mantener las tarjetas actuales del dashboard:
        # - total_ingresos_est: interpretamos como cantidad de pacientes con alguna ficha en el establecimiento
        total_ingresos_est = fichas_qs.values('paciente').distinct().count()
        total_fichas_est = fichas_qs.count()

        # Cambios recientes en pacientes (últimos 7 días)
        last_7 = timezone.now() - timedelta(days=7)
        cambios_recientes_count = Paciente.history.filter(history_date__gte=last_7).count()

        # Pacientes recientes según las últimas fichas creadas en este establecimiento (top 10)
        fichas_recientes = fichas_qs.order_by('-created_at')[:10]
        pacientes_recientes = []
        for ficha in fichas_recientes:
            pac = ficha.paciente
            pacientes_recientes.append({
                'paciente': pac,
                # Para compatibilidad con la plantilla, usamos la propia ficha como "ingreso"
                'ingreso': ficha,
                'ficha': ficha,
                'numero_ficha': (str(ficha.numero_ficha_sistema).zfill(4)
                                 if ficha and ficha.numero_ficha_sistema is not None else None)
            })

        # Last 5 changes using django-simple-history
        history_items = Paciente.history.all().order_by('-history_date')[:5]
        cambios = []
        for h in history_items:
            prev = h.prev_record
            campo = None
            antes = None
            despues = None
            if prev:
                # Try to detect first changed simple field
                for field in Paciente._meta.fields:
                    fname = field.name
                    try:
                        v_prev = getattr(prev, fname)
                        v_cur = getattr(h, fname)
                    except Exception:
                        continue
                    if v_prev != v_cur:
                        campo = fname
                        antes = v_prev
                        despues = v_cur
                        break
            cambios.append({
                'paciente_str': str(h.instance) if hasattr(h, 'instance') else (h.rut or ''),
                'campo': campo,
                'antes': antes,
                'despues': despues,
                'fecha': h.history_date,
                'usuario': getattr(h.history_user, 'username', None) if hasattr(h, 'history_user') else None,
            })

        ctx.update({
            'title': 'Dashboard',
            'user_nombre': user.get_username(),
            'establecimiento': establecimiento,
            'rol': rol,
            'total_pacientes': total_pacientes,
            'total_ingresos_est': total_ingresos_est,
            'total_fichas_est': total_fichas_est,
            'cambios_recientes_count': cambios_recientes_count,
            'pacientes_recientes': pacientes_recientes,
            'cambios': cambios,
        })
        return ctx
