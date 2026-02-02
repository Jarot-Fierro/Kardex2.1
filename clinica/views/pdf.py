import base64
from datetime import timedelta
from io import BytesIO
from types import SimpleNamespace

import barcode
from django.http import Http404
from django.shortcuts import render, get_object_or_404

from clinica.models import Ficha
from clinica.models import MovimientoFicha
from personas.models.pacientes import Paciente


def pdf_index(request, ficha_id=None, paciente_id=None):
    ficha = None

    if ficha_id is not None:
        ficha = get_object_or_404(Ficha, id=ficha_id)
        paciente = ficha.paciente
    elif paciente_id is not None:
        paciente = get_object_or_404(Paciente, id=paciente_id)
        # Obtener la ficha asociada al establecimiento del usuario logueado
        establecimiento = getattr(request.user, 'establecimiento', None)
        if establecimiento is None:
            raise Http404("El usuario no tiene un establecimiento asociado")
        ficha = Ficha.objects.filter(
            paciente=paciente,
            establecimiento=establecimiento
        ).first()
        if ficha is None:
            raise Http404("El paciente no tiene una ficha asociada para el establecimiento del usuario")
    else:
        # Si no se proporciona ningún ID, retornar 404
        raise Http404("Se requiere ficha")

    # Compatibilidad con plantillas antiguas: proporcionar atributos esperados
    if not hasattr(ficha, 'numero_ficha'):
        ficha.numero_ficha = ficha.numero_ficha_sistema
    if not hasattr(ficha, 'ingreso_paciente'):
        ficha.ingreso_paciente = SimpleNamespace(
            establecimiento=ficha.establecimiento,
            paciente=ficha.paciente,
        )

    # Generar código de barras basado en el número de RUT del paciente
    rut_paciente = getattr(paciente, 'rut', '') or ''
    numero_rut = obtener_numero_rut(rut_paciente)
    # Fallbacks por si no hay RUT válido
    if not numero_rut:
        # Usar el código interno de paciente si existe, de lo contrario el número de ficha del sistema
        numero_rut = (
                getattr(paciente, 'codigo', '') or str(getattr(ficha, 'numero_ficha_sistema', '') or '')).strip()
    codigo_barras_base64 = generar_barcode_base64(numero_rut)

    context = {
        'paciente': paciente,
        'ficha': ficha,
        'codigo_barras_base64': codigo_barras_base64
    }

    return render(request, 'pdfs/formato_caratula.html', context)


def pdf_stickers(request, ficha_id=None, paciente_id=None):
    ficha = None

    if ficha_id is not None:
        ficha = get_object_or_404(Ficha, id=ficha_id)
        paciente = ficha.paciente
    elif paciente_id is not None:
        paciente = get_object_or_404(Paciente, id=paciente_id)
        # Obtener la ficha asociada al establecimiento del usuario logueado
        establecimiento = getattr(request.user, 'establecimiento', None)
        if establecimiento is None:
            raise Http404("El usuario no tiene un establecimiento asociado")
        ficha = Ficha.objects.filter(
            paciente=paciente,
            establecimiento=establecimiento
        ).first()
        if ficha is None:
            raise Http404("El paciente no tiene una ficha asociada para el establecimiento del usuario")
    else:
        # Si no se proporciona ningún ID, retornar 404
        raise Http404("Se requiere ficha")

    # Compatibilidad con plantillas antiguas: proporcionar atributos esperados
    if not hasattr(ficha, 'numero_ficha'):
        ficha.numero_ficha = ficha.numero_ficha_sistema
    if not hasattr(ficha, 'ingreso_paciente'):
        ficha.ingreso_paciente = SimpleNamespace(
            establecimiento=ficha.establecimiento,
            paciente=ficha.paciente,
        )

    # Generar código de barras basado en el número de RUT del paciente
    rut_paciente = getattr(paciente, 'rut', '') or ''
    numero_rut = obtener_numero_rut(rut_paciente)
    # Fallbacks por si no hay RUT válido
    if not numero_rut:
        numero_rut = (
                getattr(paciente, 'codigo', '') or str(getattr(ficha, 'numero_ficha_sistema', '') or '')).strip()
    codigo_barras_base64 = generar_barcode_base64(numero_rut)

    context = {
        'paciente': paciente,
        'ficha': ficha,
        'codigo_barras_base64': codigo_barras_base64,
        'sticker_range': range(30)

    }

    return render(request, 'pdfs/formato_stickers.html', context)


def obtener_numero_rut(rut_str: str) -> str:
    if not rut_str:
        return ''
    # Normalizar: quitar separadores y conservar todos los caracteres del RUT incluyendo DV
    s = str(rut_str).strip()
    # Eliminar separadores comunes (puntos, guiones y espacios), conservar alfanuméricos
    cleaned = ''.join(ch for ch in s if ch.isalnum())
    # En Chile el DV puede ser 'K' o 'k'; normalizamos a mayúscula
    cleaned = cleaned.upper()
    return cleaned


def generar_barcode_base64(codigo_paciente: str) -> str:
    buffer = BytesIO()
    try:
        from barcode.writer import ImageWriter
        if ImageWriter is None:
            raise ImportError("ImageWriter is None")
        writer = ImageWriter()
        mime_type = "image/png"
    except (ImportError, TypeError):
        from barcode.writer import SVGWriter
        writer = SVGWriter()
        mime_type = "image/svg+xml"

    codigo = barcode.get('code128', codigo_paciente, writer=writer)
    codigo.write(buffer, options={
        "module_height": 10.0,
        "font_size": 10,
        "quiet_zone": 1,
        "write_text": False,
    })

    base64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:{mime_type};base64,{base64_data}"


def pdf_movimientos_fichas(request):
    tipo = request.GET.get('tipo', 'salida')  # salida, entrada, traspaso
    hora_inicio = request.GET.get('hora_inicio')
    hora_termino = request.GET.get('hora_termino')
    servicio_id = request.GET.get('servicio_clinico')
    profesional_id = request.GET.get('profesional')

    establecimiento = getattr(request.user, 'establecimiento', None)
    if not establecimiento:
        raise Http404("El usuario no tiene un establecimiento asociado")

    # Definir campos dinámicos según tipo
    if tipo == 'entrada':
        titulo = "Entrega Fichas – Entrada / Recepción"
        fecha_field = 'fecha_recepcion'
        servicio_field = 'servicio_clinico_recepcion'
        profesional_field = 'profesional_recepcion'
        usuario_field = 'usuario_recepcion'
        etiqueta_usuario = "Recepcionado por"
        # Para entrada, filtramos solo los recibidos
        estado_filter = {'estado_recepcion': 'RECIBIDO'}
    elif tipo == 'traspaso':
        titulo = "Entrega Fichas – Traspaso"
        fecha_field = 'fecha_traspaso'
        servicio_field = 'servicio_clinico_traspaso'
        profesional_field = 'profesional_traspaso'
        usuario_field = 'usuario_traspaso'
        etiqueta_usuario = "Traspasado por"
        estado_filter = {'estado_traspaso': 'TRASPASADO'}
    else:
        titulo = "Entrega Fichas – Salida / Envío"
        fecha_field = 'fecha_envio'
        servicio_field = 'servicio_clinico_envio'
        profesional_field = 'profesional_envio'
        usuario_field = 'usuario_envio'
        etiqueta_usuario = "Entregado por"
        estado_filter = {'estado_envio': 'ENVIADO'}

    # 1. Filtro base por establecimiento y estado
    queryset = MovimientoFicha.objects.filter(
        establecimiento=establecimiento,
        **estado_filter
    ).select_related(
        'ficha__paciente',
        servicio_field,
        profesional_field,
        usuario_field
    )

    filtros_aplicados = any([hora_inicio, hora_termino, servicio_id, profesional_id])

    # 2. Aplicar filtros si existen
    if hora_inicio:
        queryset = queryset.filter(**{f"{fecha_field}__gte": hora_inicio})
    if hora_termino:
        queryset = queryset.filter(**{f"{fecha_field}__lte": hora_termino})
    if servicio_id:
        queryset = queryset.filter(**{f"{servicio_field}_id": servicio_id})
    if profesional_id:
        queryset = queryset.filter(**{f"{profesional_field}_id": profesional_id})

    # Ordenar por fecha descendente
    queryset = queryset.order_by(f'-{fecha_field}')

    # 3. Aplicar límites
    if not filtros_aplicados:
        # Regla de separación temporal: 2 semanas (solo si no hay filtros)
        primer_mov = queryset.first()
        if primer_mov:
            ultima_fecha = getattr(primer_mov, fecha_field)
            if ultima_fecha:
                limite_temporal = ultima_fecha - timedelta(weeks=2)
                queryset = queryset.filter(**{f"{fecha_field}__gte": limite_temporal})

    # Límites solicitados: 3 servicios, 2 profesionales, 10 fichas
    limit_servicios = 3
    limit_profesionales = 2
    limit_fichas = 10

    # 4. Agrupación de datos eficiente
    datos_agrupados = []

    # Agrupamos en memoria para evitar múltiples hits a la DB
    count_servicios = 0
    servicios_map = {}  # {servicio_id: {obj, profesionales_map, order}}

    for m in queryset:
        s_obj = getattr(m, servicio_field)
        if not s_obj: continue

        s_id = s_obj.id
        if s_id not in servicios_map:
            if limit_servicios and count_servicios >= limit_servicios:
                continue
            servicios_map[s_id] = {
                'obj': s_obj,
                'profesionales_map': {},
                'profesionales_count': 0,
                'order': count_servicios
            }
            count_servicios += 1

        s_data = servicios_map[s_id]
        p_obj = getattr(m, profesional_field)
        if not p_obj: continue

        p_id = p_obj.id
        if p_id not in s_data['profesionales_map']:
            if limit_profesionales and s_data['profesionales_count'] >= limit_profesionales:
                continue
            s_data['profesionales_map'][p_id] = {
                'obj': p_obj,
                'movimientos': [],
                'order': s_data['profesionales_count']
            }
            s_data['profesionales_count'] += 1

        p_data = s_data['profesionales_map'][p_id]
        if limit_fichas and len(p_data['movimientos']) >= limit_fichas:
            continue

        usuario = getattr(m, usuario_field)
        p_data['movimientos'].append({
            'numero_ficha': m.ficha.numero_ficha_sistema if m.ficha else 'N/A',
            'rut_paciente': m.ficha.paciente.rut if m.ficha and m.ficha.paciente else 'N/A',
            'nombre_paciente': m.ficha.paciente.nombre_completo if m.ficha and m.ficha.paciente else 'N/A',
            'hora_movimiento': getattr(m, fecha_field),
            'usuario_responsable': str(usuario) if usuario else 'N/A',
        })

    # Convertir mapas a listas ordenadas para el template
    servicios_sorted = sorted(servicios_map.values(), key=lambda x: x['order'])
    for s in servicios_sorted:
        profs_sorted = sorted(s['profesionales_map'].values(), key=lambda x: x['order'])
        profesionales_list = []
        for p in profs_sorted:
            profesionales_list.append({
                'nombre': str(p['obj']),
                'movimientos': p['movimientos']
            })

        datos_agrupados.append({
            'nombre': s['obj'].nombre,
            'profesionales': profesionales_list
        })

    subtitulo = "Historial completo"
    if hora_inicio and hora_termino:
        subtitulo = f"Desde {hora_inicio} hasta {hora_termino}"
    elif hora_inicio:
        subtitulo = f"Desde {hora_inicio}"
    elif hora_termino:
        subtitulo = f"Hasta {hora_termino}"
    elif not filtros_aplicados:
        subtitulo = "Últimos movimientos registrados"

    context = {
        'titulo_movimiento': titulo,
        'subtitulo_filtros': subtitulo,
        'etiqueta_usuario': etiqueta_usuario,
        'servicios': datos_agrupados,
    }

    return render(request, 'pdfs/movimientos_fichas.html', context)
