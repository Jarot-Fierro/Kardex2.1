from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse

from clinica.models import Ficha, MovimientoFicha


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
        en_transito = MovimientoFicha.objects.filter(
            ficha=ficha,
            estado_recepcion='EN ESPERA',
            establecimiento=establecimiento
        ).exists()

        results.append({
            'paciente_id': paciente.id,
            'ficha_id': ficha.id,
            'rut': ficha.paciente.rut,  # Usar el RUT formateado del paciente
            'numero_ficha_sistema': ficha.numero_ficha_sistema,
            'nombre_completo': f"{paciente.nombre} {paciente.apellido_paterno} {paciente.apellido_materno}".strip(),
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
            'nombre_completo': f"{paciente.nombre} {paciente.apellido_paterno} {paciente.apellido_materno}".strip(),
            'servicio_envio_id': ultimo_movimiento.servicio_clinico_envio_id if ultimo_movimiento else None,
            'servicio_envio_nombre': ultimo_movimiento.servicio_clinico_envio.nombre if ultimo_movimiento and ultimo_movimiento.servicio_clinico_envio else '',
            'servicio_recepcion_id': ultimo_movimiento.servicio_clinico_recepcion_id if ultimo_movimiento else None,
            'servicio_recepcion_nombre': ultimo_movimiento.servicio_clinico_recepcion.nombre if ultimo_movimiento and ultimo_movimiento.servicio_clinico_recepcion else '',
            'en_espera': ultimo_movimiento is not None,
        })

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
            'nombre_completo': f"{paciente.nombre} {paciente.apellido_paterno} {paciente.apellido_materno}".strip(),
            'servicio_envio_id': ultimo_movimiento.servicio_clinico_envio_id if ultimo_movimiento else None,
            'servicio_envio_nombre': ultimo_movimiento.servicio_clinico_envio.nombre if ultimo_movimiento and ultimo_movimiento.servicio_clinico_envio else '',
            'servicio_recepcion_id': ultimo_movimiento.servicio_clinico_recepcion_id if ultimo_movimiento else None,
            'servicio_recepcion_nombre': ultimo_movimiento.servicio_clinico_recepcion.nombre if ultimo_movimiento and ultimo_movimiento.servicio_clinico_recepcion else '',
            'estado_recepcion': ultimo_movimiento.estado_recepcion if ultimo_movimiento else '',
            'apto_traspaso': ultimo_movimiento is not None,
        })

    return JsonResponse({'results': results})
