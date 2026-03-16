from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.generic.base import TemplateView

from clinica.models import Ficha
from personas.models.pacientes import Paciente
from users.models import UserRole


@login_required
def dashboard_view(request):
    user = request.user
    establecimiento = getattr(user, 'establecimiento', None)

    # ==========================
    # 🔍 BÚSQUEDA RÁPIDA
    # ==========================
    q = request.GET.get('q')
    if q:
        qs = Paciente.objects.filter(status=True).filter(
            Q(rut__iexact=q) |
            Q(nombre__icontains=q) |
            Q(apellido_paterno__icontains=q) |
            Q(apellido_materno__icontains=q)
        )

        if qs.count() == 1:
            return redirect('paciente_detail', pk=qs.first().pk)
        elif qs.count() == 0:
            messages.warning(request, 'No se encontraron pacientes para la búsqueda ingresada.')
        else:
            messages.info(request, 'Se encontraron múltiples pacientes. Por favor refina tu búsqueda.')

    # ==========================
    # 👤 ROL
    # ==========================
    first_group = user.groups.first()
    rol = first_group.name if first_group else getattr(user, 'tipo_perfil', None)

    # ==========================
    # 🔐 PERMISOS (SIN TOCAR)
    # ==========================
    permissions = {
        'comunas': 0,
        'establecimientos': 0,
        'fichas': 0,
        'genero': 0,
        'movimiento_ficha': 0,
        'paciente': 0,
        'pais': 0,
        'prevision': 0,
        'colores_sector': 0,
        'profesion': 0,
        'profesionales': 0,
        'sectores': 0,
        'servicio_clinico': 0,
        'soporte': 0,
    }

    user_roles = UserRole.objects.filter(user_id=user)
    for user_role in user_roles:
        role = user_role.role_id
        for module in permissions:
            current = getattr(role, module, 0)
            if current > permissions[module]:
                permissions[module] = current

    # ==========================
    # 🕒 CAMBIOS RECIENTES
    # ==========================
    last_7 = timezone.now() - timedelta(days=7)
    cambios_recientes_count = Paciente.history.filter(
        history_date__gte=last_7
    ).count()

    history_items = Paciente.history.order_by('-history_date')[:5]
    cambios = []

    for h in history_items:
        prev = h.prev_record
        campo = antes = despues = None

        if prev:
            for field in Paciente._meta.fields:
                fname = field.name
                try:
                    if getattr(prev, fname) != getattr(h, fname):
                        campo = fname
                        antes = getattr(prev, fname)
                        despues = getattr(h, fname)
                        break
                except Exception:
                    continue

        cambios.append({
            'paciente_str': str(h.instance) if hasattr(h, 'instance') else h.rut,
            'campo': campo,
            'antes': antes,
            'despues': despues,
            'fecha': h.history_date,
            'usuario': getattr(h.history_user, 'username', None),
        })

    # ==========================
    # 🧾 PACIENTES RECIENTES
    # ==========================
    fichas_recientes = Ficha.objects.all().order_by('-created_at')[:10]
    pacientes_recientes = []

    for ficha in fichas_recientes:
        pacientes_recientes.append({
            'paciente': ficha.paciente,
            'ingreso': ficha,
            'ficha': ficha,
            'numero_ficha': (
                str(ficha.numero_ficha_sistema).zfill(4)
                if ficha.numero_ficha_sistema is not None
                else None
            )
        })

    # ==========================
    # 📦 CONTEXTO FINAL (SEPARADO)
    # ==========================
    context = {
        'permissions': permissions,
        'title': 'Dashboard',
        'user_nombre': user.get_username(),
        'establecimiento': establecimiento,
        'rol': rol,
        'cambios_recientes_count': cambios_recientes_count,
        'pacientes_recientes': pacientes_recientes,
        'cambios': cambios,
    }

    return render(request, 'core/dashboard.html', context)


@login_required
def dashboard_metrics_view(request):
    """
    Vista asíncrona para cargar las métricas pesadas del dashboard.
    Retorna un JsonResponse con las métricas calculadas.
    Incluye caché de 5 minutos por establecimiento.
    """
    user = request.user
    establecimiento = getattr(user, 'establecimiento', None)
    est_id = establecimiento.id if establecimiento else 'global'

    cache_key = f'dashboard_metrics_{est_id}'
    data = cache.get(cache_key)

    if not data:
        # 1. Total Pacientes: Global y Activos (status=True)
        total_pacientes = Paciente.objects.filter(status=True).count()

        # 2. Métricas por Establecimiento
        total_ingresos_est = 0
        total_fichas_est = 0

        if establecimiento:
            # Query base filtrando por establecimiento y pacientes activos
            fichas_qs = Ficha.objects.filter(
                establecimiento=establecimiento,
                paciente__status=True
            )

            # Cantidad de pacientes distintos con ficha en ese establecimiento
            total_ingresos_est = fichas_qs.values('paciente_id').distinct().count()

            # Total de fichas del establecimiento
            total_fichas_est = fichas_qs.count()

        data = {
            'total_pacientes': total_pacientes,
            'total_ingresos_est': total_ingresos_est,
            'total_fichas_est': total_fichas_est,
        }

        # Cache por 5 minutos (300 segundos)
        cache.set(cache_key, data, 300)

    return JsonResponse(data)


@login_required
def maintenance_view(request):
    return render(request, 'core/maintenance.html')


@login_required
def no_establecimiento(request):
    return render(request, 'core/no_establecimiento.html')


class ContactoView(LoginRequiredMixin, TemplateView):
    template_name = 'contacto/contacto.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Contacto',
        })
        return context
