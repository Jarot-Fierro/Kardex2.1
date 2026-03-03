from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from clinica.models import Ficha, MovimientoFicha
from clinica.models.movimiento_ficha_monologo_controlado import MovimientoMonologoControlado


@login_required
def buscar_paciente_ficha_api(request):
    """
    API para buscar un paciente por RUT o número de ficha en el establecimiento del usuario.
    Específicamente para el módulo de Salida de Fichas.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    # Normalizar búsqueda para comparar con RUT o número de ficha
    # El usuario indica que se guarda con puntos y guion (20.930.055-9)
    query_upper = query.upper()

    # También generamos una versión sin puntos ni guion para el caso de búsqueda por número de ficha
    query_clean = query.replace('.', '').replace('-', '').strip()

    establecimiento = getattr(request.user, 'establecimiento', None)
    if not establecimiento:
        return JsonResponse({'error': 'Usuario no tiene establecimiento asociado'}, status=403)

    # Buscar fichas que coincidan con el RUT del paciente (tal cual viene o formateado)
    # o el número de ficha del sistema
    filtros = Q(paciente__rut=query_upper) | Q(paciente__rut=query_clean) | Q(paciente__rut=query_upper.lower()) | Q(
        paciente__rut=query_clean.lower())

    if query_clean.isdigit() or (query_upper.startswith('PAC-') and query_upper[4:].isdigit()):
        try:
            val = query_upper
            if val.startswith('PAC-'):
                val = int(val[4:])
            else:
                val = int(query_clean)
            filtros |= Q(numero_ficha_sistema=val)
        except:
            pass

    fichas = Ficha.objects.filter(
        filtros,
        establecimiento=establecimiento
    ).select_related('paciente').distinct()

    results = []
    for ficha in fichas:
        paciente = ficha.paciente

        # Validar si tiene movimientos en tránsito (EN ESPERA de recepción)
        en_transito_old = MovimientoFicha.objects.filter(
            ficha=ficha,
            estado_recepcion='EN ESPERA',
            establecimiento=establecimiento
        ).exists()

        en_transito = en_transito_old

        results.append({
            'paciente_id': paciente.id,
            'ficha_id': ficha.id,
            'rut': ficha.paciente.rut,  # Usar el RUT formateado del paciente
            'numero_ficha_sistema': ficha.numero_ficha_sistema,
            'nombre_completo': paciente.nombre_completo,
            'en_transito': en_transito,
        })

    return JsonResponse({'results': results})


@login_required
def buscar_paciente_ficha_api_monologo(request):
    """
    API para buscar un paciente por RUT o número de ficha en el establecimiento del usuario.
    Específicamente para el módulo de Salida de Fichas.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    # Normalizar búsqueda para comparar con RUT o número de ficha
    # El usuario indica que se guarda con puntos y guion (20.930.055-9)
    query_upper = query.upper()

    # También generamos una versión sin puntos ni guion para el caso de búsqueda por número de ficha
    query_clean = query.replace('.', '').replace('-', '').strip()

    establecimiento = getattr(request.user, 'establecimiento', None)
    if not establecimiento:
        return JsonResponse({'error': 'Usuario no tiene establecimiento asociado'}, status=403)

    # Buscar fichas que coincidan con el RUT del paciente (tal cual viene o formateado)
    # o el número de ficha del sistema
    filtros = Q(paciente__rut=query_upper) | Q(paciente__rut=query_clean) | Q(paciente__rut=query_upper.lower()) | Q(
        paciente__rut=query_clean.lower())

    if query_clean.isdigit() or (query_upper.startswith('PAC-') and query_upper[4:].isdigit()):
        try:
            val = query_upper
            if val.startswith('PAC-'):
                val = int(val[4:])
            else:
                val = int(query_clean)
            filtros |= Q(numero_ficha_sistema=val)
        except:
            pass

    fichas = Ficha.objects.filter(
        filtros,
        establecimiento=establecimiento
    ).select_related('paciente').distinct()

    results = []
    for ficha in fichas:
        paciente = ficha.paciente

        # Validar si tiene movimientos en tránsito (EN ESPERA de recepción)

        en_transito_new = MovimientoMonologoControlado.objects.filter(
            ficha=ficha,
            estado='E',
            status=True
        ).exists()

        en_transito = en_transito_new

        results.append({
            'paciente_id': paciente.id,
            'ficha_id': ficha.id,
            'rut': ficha.paciente.rut,  # Usar el RUT formateado del paciente
            'numero_ficha_sistema': ficha.numero_ficha_sistema,
            'nombre_completo': paciente.nombre_completo,
            'en_transito': en_transito,
        })

    return JsonResponse({'results': results})


@login_required
def buscar_paciente_recepcion_api(request):
    """
    API para buscar un paciente por RUT o número de ficha y obtener su último movimiento ENVIADO.
    Para el módulo de Recepción de Fichas.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    query_upper = query.upper()
    query_clean = query.replace('.', '').replace('-', '').strip()

    establecimiento = getattr(request.user, 'establecimiento', None)
    if not establecimiento:
        return JsonResponse({'error': 'Usuario no tiene establecimiento asociado'}, status=403)

    filtros = Q(paciente__rut=query_upper) | Q(paciente__rut=query_clean) | Q(paciente__rut=query_upper.lower()) | Q(
        paciente__rut=query_clean.lower())

    if query_clean.isdigit() or (query_upper.startswith('PAC-') and query_upper[4:].isdigit()):
        try:
            val = query_upper
            if val.startswith('PAC-'):
                val = int(val[4:])
            else:
                val = int(query_clean)
            filtros |= Q(numero_ficha_sistema=val)
        except:
            pass

    fichas = Ficha.objects.filter(
        filtros,
        establecimiento=establecimiento
    ).select_related('paciente').distinct()

    results = []
    for ficha in fichas:
        paciente = ficha.paciente

        # Buscar el último movimiento que esté en estado 'ENVIADO' y en espera de recepción
        ultimo_movimiento = MovimientoFicha.objects.filter(
            ficha=ficha,
            estado_envio='ENVIADO',
            estado_recepcion='EN ESPERA',
            establecimiento=establecimiento
        ).order_by('-fecha_envio').first()

        results.append({
            'paciente_id': paciente.id,
            'ficha_id': ficha.id,
            'movimiento_id': ultimo_movimiento.id if ultimo_movimiento else None,
            'rut': ficha.paciente.rut,
            'numero_ficha_sistema': ficha.numero_ficha_sistema,
            'nombre_completo': paciente.nombre_completo,
            'servicio_envio_id': ultimo_movimiento.servicio_clinico_envio_id if ultimo_movimiento else None,
            'servicio_envio_nombre': ultimo_movimiento.servicio_clinico_envio.nombre if ultimo_movimiento and ultimo_movimiento.servicio_clinico_envio else '',
            'servicio_recepcion_id': ultimo_movimiento.servicio_clinico_recepcion_id if ultimo_movimiento else None,
            'servicio_recepcion_nombre': ultimo_movimiento.servicio_clinico_recepcion.nombre if ultimo_movimiento and ultimo_movimiento.servicio_clinico_recepcion else '',
            'en_espera': ultimo_movimiento is not None,
        })

    return JsonResponse({'results': results})


@login_required
def buscar_paciente_recepcion_api_monologo(request):
    """
    API para buscar un paciente por RUT o número de ficha y obtener su último movimiento ENVIADO.
    Para el módulo de Recepción de Fichas.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    query_upper = query.upper()
    query_clean = query.replace('.', '').replace('-', '').strip()

    establecimiento = getattr(request.user, 'establecimiento', None)
    if not establecimiento:
        return JsonResponse({'error': 'Usuario no tiene establecimiento asociado'}, status=403)

    filtros = Q(paciente__rut=query_upper) | Q(paciente__rut=query_clean) | Q(paciente__rut=query_upper.lower()) | Q(
        paciente__rut=query_clean.lower())

    if query_clean.isdigit() or (query_upper.startswith('PAC-') and query_upper[4:].isdigit()):
        try:
            val = query_upper
            if val.startswith('PAC-'):
                val = int(val[4:])
            else:
                val = int(query_clean)
            filtros |= Q(numero_ficha_sistema=val)
        except:
            pass

    fichas = Ficha.objects.filter(
        filtros,
        establecimiento=establecimiento
    ).select_related('paciente').distinct()

    results = []
    for ficha in fichas:
        paciente = ficha.paciente

        # Buscar el último movimiento que esté en estado 'ENVIADO' y en espera de recepción
        # We prioritize the NEW system (MovimientoMonologoControlado)
        movimiento = MovimientoMonologoControlado.objects.filter(
            ficha=ficha,
            estado='E',
            establecimiento=establecimiento,
            status=True
        ).select_related('servicio_clinico_destino', 'profesional').first()

        if movimiento:
            results.append({
                'paciente_id': paciente.id,
                'ficha_id': ficha.id,
                'rut': paciente.rut,
                'numero_ficha_sistema': ficha.numero_ficha_sistema,
                'nombre_completo': paciente.nombre_completo,
                'movimiento_id': movimiento.id,
                # Campos para la nueva vista
                'servicio_clinico_actual': movimiento.servicio_clinico_destino.nombre,
                'profesional_asignado': str(movimiento.profesional),
                # Campos legacy por si acaso
                'servicio_envio_nombre': 'SOME (Origen)',
                'servicio_recepcion_nombre': movimiento.servicio_clinico_destino.nombre,
                'en_espera': True
            })
        else:
            # Fallback check old system? The user implies moving TO the new system.
            # If we want to support both, we should check MovimientoFicha here too if MovimientoMonologoControlado is empty.
            # For now, let's assume we are fully testing the new system as requested.
            pass

    return JsonResponse({'results': results})


@login_required
def buscar_paciente_traspaso_api(request):
    """
    API para buscar un paciente por RUT o número de ficha y obtener su último movimiento (ENVIADO o RECIBIDO).
    Para el módulo de Traspaso de Fichas.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    query_upper = query.upper()
    query_clean = query.replace('.', '').replace('-', '').strip()

    establecimiento = getattr(request.user, 'establecimiento', None)
    if not establecimiento:
        return JsonResponse({'error': 'Usuario no tiene establecimiento asociado'}, status=403)

    filtros = Q(paciente__rut=query_upper) | Q(paciente__rut=query_clean) | Q(paciente__rut=query_upper.lower()) | Q(
        paciente__rut=query_clean.lower())

    if query_clean.isdigit() or (query_upper.startswith('PAC-') and query_upper[4:].isdigit()):
        try:
            val = query_upper
            if val.startswith('PAC-'):
                val = int(val[4:])
            else:
                val = int(query_clean)
            filtros |= Q(numero_ficha_sistema=val)
        except:
            pass

    fichas = Ficha.objects.filter(
        filtros,
        establecimiento=establecimiento
    ).select_related('paciente').distinct()

    results = []
    for ficha in fichas:
        paciente = ficha.paciente

        # Buscar el último movimiento que esté en estado ENVIADO o RECIBIDO y no haya sido traspasado aún
        ultimo_movimiento = MovimientoFicha.objects.filter(
            ficha=ficha,
            estado_recepcion__in=['EN ESPERA', 'RECIBIDO'],
            establecimiento=establecimiento
        ).exclude(
            estado_traspaso='TRASPASADO'
        ).order_by('-created_at').first()

        results.append({
            'paciente_id': paciente.id,
            'ficha_id': ficha.id,
            'movimiento_id': ultimo_movimiento.id if ultimo_movimiento else None,
            'rut': ficha.paciente.rut,
            'numero_ficha_sistema': ficha.numero_ficha_sistema,
            'nombre_completo': paciente.nombre_completo,
            'servicio_envio_id': ultimo_movimiento.servicio_clinico_envio_id if ultimo_movimiento else None,
            'servicio_envio_nombre': ultimo_movimiento.servicio_clinico_envio.nombre if ultimo_movimiento and ultimo_movimiento.servicio_clinico_envio else '',
            'servicio_recepcion_id': ultimo_movimiento.servicio_clinico_recepcion_id if ultimo_movimiento else None,
            'servicio_recepcion_nombre': ultimo_movimiento.servicio_clinico_recepcion.nombre if ultimo_movimiento and ultimo_movimiento.servicio_clinico_recepcion else '',
            'estado_recepcion': ultimo_movimiento.estado_recepcion if ultimo_movimiento else '',
            'apto_traspaso': ultimo_movimiento is not None,
        })

    return JsonResponse({'results': results})


@login_required
def buscar_paciente_ficha_api_monologo_traspaso(request):
    """
    API para buscar un paciente y su movimiento monólogo controlado más reciente
    en el establecimiento del usuario, sin importar el estado.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    query_upper = query.upper()
    query_clean = query.replace('.', '').replace('-', '').strip()

    establecimiento = getattr(request.user, 'establecimiento', None)
    if not establecimiento:
        return JsonResponse({'error': 'Usuario no tiene establecimiento asociado'}, status=403)

    filtros = Q(paciente__rut=query_upper) | Q(paciente__rut=query_clean) | Q(paciente__rut=query_upper.lower()) | Q(
        paciente__rut=query_clean.lower())

    if query_clean.isdigit() or (query_upper.startswith('PAC-') and query_upper[4:].isdigit()):
        try:
            val = query_upper
            if val.startswith('PAC-'):
                val = int(val[4:])
            else:
                val = int(query_clean)
            filtros |= Q(numero_ficha_sistema=val)
        except:
            pass

    fichas = Ficha.objects.filter(
        filtros,
        establecimiento=establecimiento
    ).select_related('paciente').distinct()

    results = []
    for ficha in fichas:
        paciente = ficha.paciente

        # Buscar el movimiento monólogo más reciente para esta ficha y este establecimiento
        ultimo_movimiento = MovimientoMonologoControlado.objects.filter(
            ficha=ficha,
            establecimiento=establecimiento,
            estado='E',
            status=True
        ).order_by('-fecha_salida').first()

        data = {
            'paciente_id': paciente.id,
            'ficha_id': ficha.id,
            'rut': ficha.paciente.rut,
            'numero_ficha_sistema': ficha.numero_ficha_sistema,
            'nombre_completo': paciente.nombre_completo,
        }

        if ultimo_movimiento:
            data.update({
                'movimiento_id': ultimo_movimiento.id,
                'servicio_clinico_destino': ultimo_movimiento.servicio_clinico_destino_id,
                'profesional': ultimo_movimiento.profesional_id,
                'fecha_salida': timezone.localtime(ultimo_movimiento.fecha_salida).strftime(
                    '%Y-%m-%dT%H:%M') if ultimo_movimiento.fecha_salida else '',
                'fecha_entrada': ultimo_movimiento.fecha_entrada.strftime(
                    '%Y-%m-%dT%H:%M') if ultimo_movimiento.fecha_entrada else '',
                'observacion_traspaso': ultimo_movimiento.observacion_traspaso or '',
            })

        results.append(data)

    return JsonResponse({'results': results})


@login_required
def buscar_paciente_general_api(request):
    """
    API general para buscar pacientes por RUT o número de ficha y devolver sus datos básicos.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    query_upper = query.upper()
    query_clean = query.replace('.', '').replace('-', '').strip()

    establecimiento = getattr(request.user, 'establecimiento', None)
    if not establecimiento:
        return JsonResponse({'error': 'Usuario no tiene establecimiento asociado'}, status=403)

    filtros = Q(paciente__rut__icontains=query_clean) | Q(paciente__nombre__icontains=query_upper) | \
              Q(paciente__apellido_paterno__icontains=query_upper) | Q(
        paciente__apellido_materno__icontains=query_upper)

    if query_clean.isdigit():
        try:
            val = int(query_clean)
            filtros |= Q(numero_ficha_sistema=val)
        except:
            pass

    fichas = Ficha.objects.filter(
        filtros,
        establecimiento=establecimiento
    ).select_related('paciente', 'paciente__comuna', 'paciente__prevision').distinct()[:20]

    results = []
    for ficha in fichas:
        p = ficha.paciente
        results.append({
            'id': p.id,
            'text': f"Ficha {ficha.numero_ficha_sistema} - {p.nombre_completo} ({p.rut})",
            'paciente_id': p.id,
            'ficha_id': ficha.id,
            'rut': p.rut,
            'numero_ficha_sistema': ficha.numero_ficha_sistema,
            'nombre_completo': p.nombre_completo,
            'fecha_nacimiento': p.fecha_nacimiento.strftime('%d/%m/%Y') if p.fecha_nacimiento else 'N/A',
            'sexo': p.sexo,
            'direccion': p.direccion or 'No informada',
            'comuna': p.comuna.nombre if p.comuna else 'N/A',
            'prevision': p.prevision.nombre if p.prevision else 'N/A',
            'telefono': p.numero_telefono1 or p.numero_telefono2 or 'N/A',
            'pasivado': ficha.pasivado,
        })

    return JsonResponse({'results': results})
