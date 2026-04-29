import base64
from datetime import timedelta
from io import BytesIO
from types import SimpleNamespace

import barcode
from barcode.writer import ImageWriter
from django.http import Http404, HttpResponse
from django.shortcuts import render, get_object_or_404
from reportlab.graphics.barcode import code128
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph

from clinica.models import Ficha
from clinica.models import MovimientoFicha
from clinica.models.movimiento_ficha_monologo_controlado import MovimientoMonologoControlado
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


def pdf_index_rn(request, ficha_id=None, paciente_id=None):
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

    return render(request, 'pdfs/formato_caratula_rn.html', context)



def pdf_caratula_reportlab(request, ficha_id=None, paciente_id=None):
    ficha = None

    if ficha_id is not None:
        ficha = get_object_or_404(Ficha, id=ficha_id)
        paciente = ficha.paciente
    elif paciente_id is not None:
        paciente = get_object_or_404(Paciente, id=paciente_id)
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
        raise Http404("Se requiere ficha")

    # Preparar respuesta PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="caratula_{paciente.rut or paciente.id}.pdf"'

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Margen de 1.5 cm aprox (50px era en HTML)
    margin = 1 * cm
    top_margin = height - margin

    # 1. Encabezado (Número Ficha, Barcode, Fecha)
    # Número Ficha
    p.setFont("Helvetica-Bold", 40)
    numero = ficha.numero_ficha_sistema or 0
    num_ficha_str = f"{numero:,}".replace(",", ".")
    # El HTML tiene un line-height de 0.8 y margin-top 0
    p.drawString(margin, top_margin - 1.4 * cm, num_ficha_str)

    # Código de Barras
    rut_paciente = getattr(paciente, 'rut', '') or ''
    numero_rut = obtener_numero_rut(rut_paciente)
    if not numero_rut:
        numero_rut = (getattr(paciente, 'codigo', '') or str(getattr(ficha, 'numero_ficha_sistema', '') or '')).strip()

    # En HTML max-height: 90px (~2.4cm)
    barcode_obj = code128.Code128(numero_rut, barHeight=1.5 * cm, barWidth=1.2)
    barcode_width = barcode_obj.width
    barcode_x = (width - barcode_width) / 2
    barcode_obj.drawOn(p, barcode_x, top_margin - 1.8 * cm)

    # Tabla Fecha Creación (Esquina superior derecha)
    styles = getSampleStyleSheet()
    fecha_creacion = ficha.fecha_creacion_anterior or ficha.created_at
    fecha_str = fecha_creacion.strftime("%d/%m/%Y") if fecha_creacion else "-"
    
    style_fecha_label = ParagraphStyle(
        'FechaLabel',
        parent=styles['Normal'],
        fontSize=11,
        alignment=1, # Center
        fontName='Helvetica-Bold'
    )
    style_fecha_value = ParagraphStyle(
        'FechaValue',
        parent=styles['Normal'],
        fontSize=12,
        alignment=1, # Center
    )

    data_fecha = [
        [Paragraph("Fecha Creación", style_fecha_label)],
        [Paragraph(fecha_str, style_fecha_value)]
    ]
    table_fecha = Table(data_fecha, colWidths=[3.8 * cm], rowHeights=[0.6 * cm, 0.7 * cm])
    table_fecha.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]), 
    ]))
    tw, th = table_fecha.wrap(0, 0)
    table_fecha.drawOn(p, width - margin - tw, top_margin - th)

    # 2. Tabla Principal de Datos
    styles = getSampleStyleSheet()
    style_label = ParagraphStyle(
        'CustomLabel',
        parent=styles['Normal'],
        fontSize=11,
        leading=12,
        fontName='Helvetica-Bold'
    )
    
    style_value = ParagraphStyle(
        'CustomValue',
        parent=styles['Normal'],
        fontSize=12,
        leading=14,
        fontName='Helvetica'
    )

    style_value_bold = ParagraphStyle(
        'CustomValueBold',
        parent=style_value,
        fontName='Helvetica-Bold'
    )
    
    style_value_red = ParagraphStyle(
        'CustomValueRed',
        parent=style_value_bold,
        textColor=colors.red
    )

    style_header_h1 = ParagraphStyle(
        'HeaderH1',
        parent=styles['Normal'],
        fontSize=20,
        leading=22,
        fontName='Helvetica-Bold'
    )

    style_header_h2 = ParagraphStyle(
        'HeaderH2',
        parent=styles['Normal'],
        fontSize=18,
        leading=20,
        fontName='Helvetica-Bold'
    )

    def make_cell(label, value, value_style=style_value):
        return [Paragraph(label, style_label), Paragraph(str(value or "-"), value_style)]

    data = [
        # Fila 1: Establecimiento / RUT | Ficha / Pasaporte
        [
            [Paragraph(getattr(ficha.establecimiento, 'nombre', '-'), style_header_h2),
             Paragraph(f"R.U.T: {paciente.rut or '-'}", style_header_h1)],
            '',
            [Paragraph(f"Ficha: {num_ficha_str}", style_header_h2),
             Paragraph(f"<b>Pasaporte: {paciente.pasaporte or '-'}</b>", style_value_bold)],
            ''
        ],
        # Fila 2: Nombre Completo | Sexo | Estado Civil
        [
            make_cell("Apellido Paterno, Apellido Materno, Nombres", 
                      f"{paciente.apellido_paterno or ''} {paciente.apellido_materno or ''} {paciente.nombre or ''}",
                      style_value_bold),
            '',
            make_cell("Sexo", paciente.get_sexo_display() if hasattr(paciente, 'get_sexo_display') else paciente.sexo),
            make_cell("Estado Civil", paciente.get_estado_civil_display() if hasattr(paciente, 'get_estado_civil_display') else paciente.estado_civil)
        ],
        # Fila 3: Fecha Nacimiento | Fecha Fallecimiento
        [
            make_cell("Fecha de Nacimiento", paciente.fecha_nacimiento.strftime("%d/%m/%Y") if paciente.fecha_nacimiento else "-"),
            '',
            make_cell("Fecha de Fallecimiento", 
                      paciente.fecha_fallecimiento.strftime("%d/%m/%Y") if paciente.fecha_fallecimiento else "-",
                      style_value_red if paciente.fecha_fallecimiento else style_value),
            ''
        ],
        # Fila 4: Dirección | Teléfono 1 | Teléfono 2
        [
            make_cell("Dirección", f"{paciente.direccion or ''}, {paciente.comuna.nombre if paciente.comuna else ''}"),
            '',
            make_cell("N° Teléfono 1", paciente.numero_telefono1),
            make_cell("N° Teléfono 2", paciente.numero_telefono2)
        ],
        # Fila 5: Nombre Social | Nombre Madre | Nombre Padre
        [
            make_cell("Nombre Social", paciente.nombre_social),
            '',
            make_cell("Nombre Madre", paciente.nombres_madre),
            make_cell("Nombre Padre", paciente.nombres_padre)
        ],
        # Fila 6: Nombre del Cónyuge | Previsión
        [
            make_cell("Nombre del Cónyuge", paciente.nombre_pareja),
            '',
            make_cell("Previsión", paciente.prevision.nombre if paciente.prevision else "-"),
            ''
        ],
        # Fila 7: Representante Legal | Ocupación
        [
            make_cell("Representante Legal", paciente.representante_legal),
            '',
            make_cell("Ocupación", paciente.ocupacion),
            ''
        ]
    ]

    col_widths = [(width - 2 * margin) * 0.4, (width - 2 * margin) * 0.1, (width - 2 * margin) * 0.25, (width - 2 * margin) * 0.25]
    
    main_table = Table(data, colWidths=col_widths)
    main_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('SPAN', (0, 0), (1, 0)), # Establecimiento/RUT
        ('SPAN', (2, 0), (3, 0)), # Ficha/Pasaporte
        ('SPAN', (0, 1), (1, 1)), # Nombre
        ('SPAN', (0, 2), (1, 2)), # Nacimiento
        ('SPAN', (2, 2), (3, 2)), # Fallecimiento
        ('SPAN', (0, 3), (1, 3)), # Dirección
        ('SPAN', (0, 4), (1, 4)), # Nombre Social
        ('SPAN', (0, 5), (1, 5)), # Cónyuge
        ('SPAN', (2, 5), (3, 5)), # Previsión
        ('SPAN', (0, 6), (1, 6)), # Representante
        ('SPAN', (2, 6), (3, 6)), # Ocupación
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))

    tw, th = main_table.wrap(0, 0)
    # 50px de margen superior aprox 1.76cm. El header ocupa espacio.
    main_table.drawOn(p, margin, top_margin - 2 * cm - th)

    p.showPage()
    p.save()

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response


def pdf_caratula__rn_reportlab(request, ficha_id=None, paciente_id=None):
    ficha = None

    if ficha_id is not None:
        ficha = get_object_or_404(Ficha, id=ficha_id)
        paciente = ficha.paciente
    elif paciente_id is not None:
        paciente = get_object_or_404(Paciente, id=paciente_id)
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
        raise Http404("Se requiere ficha")

    # Preparar respuesta PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="caratula_{paciente.rut or paciente.id}.pdf"'

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Margen de 1.5 cm aprox (50px era en HTML)
    margin = 1 * cm
    top_margin = height - margin

    # 1. Encabezado (Número Ficha, Barcode, Fecha)
    # Número Ficha
    p.setFont("Helvetica-Bold", 40)
    numero = ficha.numero_ficha_sistema or 0
    num_ficha_str = f"{numero:,}".replace(",", ".")
    # El HTML tiene un line-height de 0.8 y margin-top 0
    p.drawString(margin, top_margin - 1.4 * cm, num_ficha_str)

    # Código de Barras
    rut_paciente = getattr(paciente, 'rut', '') or ''
    numero_rut = obtener_numero_rut(rut_paciente)
    if not numero_rut:
        numero_rut = (getattr(paciente, 'codigo', '') or str(getattr(ficha, 'numero_ficha_sistema', '') or '')).strip()

    # En HTML max-height: 90px (~2.4cm)
    barcode_obj = code128.Code128(numero_rut, barHeight=1.5 * cm, barWidth=1.2)
    barcode_width = barcode_obj.width
    barcode_x = (width - barcode_width) / 2
    barcode_obj.drawOn(p, barcode_x, top_margin - 1.8 * cm)

    # Tabla Fecha Creación (Esquina superior derecha)
    styles = getSampleStyleSheet()
    fecha_creacion = ficha.fecha_creacion_anterior or ficha.created_at
    fecha_str = fecha_creacion.strftime("%d/%m/%Y") if fecha_creacion else "-"

    style_fecha_label = ParagraphStyle(
        'FechaLabel',
        parent=styles['Normal'],
        fontSize=11,
        alignment=1,  # Center
        fontName='Helvetica-Bold'
    )
    style_fecha_value = ParagraphStyle(
        'FechaValue',
        parent=styles['Normal'],
        fontSize=12,
        alignment=1,  # Center
    )

    data_fecha = [
        [Paragraph("Fecha Creación", style_fecha_label)],
        [Paragraph(fecha_str, style_fecha_value)]
    ]
    table_fecha = Table(data_fecha, colWidths=[3.8 * cm], rowHeights=[0.6 * cm, 0.7 * cm])
    table_fecha.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    tw, th = table_fecha.wrap(0, 0)
    table_fecha.drawOn(p, width - margin - tw, top_margin - th)

    # 2. Tabla Principal de Datos
    styles = getSampleStyleSheet()
    style_label = ParagraphStyle(
        'CustomLabel',
        parent=styles['Normal'],
        fontSize=11,
        leading=12,
        fontName='Helvetica-Bold'
    )

    style_value = ParagraphStyle(
        'CustomValue',
        parent=styles['Normal'],
        fontSize=12,
        leading=14,
        fontName='Helvetica'
    )

    style_value_bold = ParagraphStyle(
        'CustomValueBold',
        parent=style_value,
        fontName='Helvetica-Bold'
    )

    style_value_red = ParagraphStyle(
        'CustomValueRed',
        parent=style_value_bold,
        textColor=colors.red
    )

    style_header_h1 = ParagraphStyle(
        'HeaderH1',
        parent=styles['Normal'],
        fontSize=20,
        leading=22,
        fontName='Helvetica-Bold'
    )

    style_header_h2 = ParagraphStyle(
        'HeaderH2',
        parent=styles['Normal'],
        fontSize=18,
        leading=20,
        fontName='Helvetica-Bold'
    )

    def make_cell(label, value, value_style=style_value):
        return [Paragraph(label, style_label), Paragraph(str(value or "-"), value_style)]

    data = [
        # Fila 1: Establecimiento / RUT | Ficha / Pasaporte
        [
            [Paragraph(getattr(ficha.establecimiento, 'nombre', '-'), style_header_h2),
             Paragraph(f"R.U.T: ", style_header_h1)],
            '',
            [Paragraph(f"Ficha: {num_ficha_str}", style_header_h2),
             Paragraph(f"<b>Pasaporte: {paciente.pasaporte or '-'}</b>", style_value_bold)],
            ''
        ],
        # Fila 2: Nombre Completo | Sexo | Estado Civil
        [
            make_cell("Apellido Paterno, Apellido Materno, Nombres",
                      f"{paciente.apellido_paterno or ''} {paciente.apellido_materno or ''} {paciente.nombre or ''}",
                      style_value_bold),
            '',
            make_cell("Sexo", paciente.get_sexo_display() if hasattr(paciente, 'get_sexo_display') else paciente.sexo),
            make_cell("Estado Civil", paciente.get_estado_civil_display() if hasattr(paciente,
                                                                                     'get_estado_civil_display') else paciente.estado_civil)
        ],
        # Fila 3: Fecha Nacimiento | Fecha Fallecimiento
        [
            make_cell("Fecha de Nacimiento",
                      paciente.fecha_nacimiento.strftime("%d/%m/%Y") if paciente.fecha_nacimiento else "-"),
            '',
            make_cell("Fecha de Fallecimiento",
                      paciente.fecha_fallecimiento.strftime("%d/%m/%Y") if paciente.fecha_fallecimiento else "-",
                      style_value_red if paciente.fecha_fallecimiento else style_value),
            ''
        ],
        # Fila 4: Dirección | Teléfono 1 | Teléfono 2
        [
            make_cell("Dirección", f"{paciente.direccion or ''}, {paciente.comuna.nombre if paciente.comuna else ''}"),
            '',
            make_cell("N° Teléfono 1", paciente.numero_telefono1),
            make_cell("N° Teléfono 2", paciente.numero_telefono2)
        ],
        # Fila 5: Nombre Social | Nombre Madre | Nombre Padre
        [
            make_cell("Nombre Social", paciente.nombre_social),
            '',
            make_cell("Nombre Madre", paciente.nombres_madre),
            make_cell("Nombre Padre", paciente.nombres_padre)
        ],
        # Fila 6: Nombre del Cónyuge | Previsión
        [
            make_cell("Nombre del Cónyuge", paciente.nombre_pareja),
            '',
            make_cell("Previsión", paciente.prevision.nombre if paciente.prevision else "-"),
            ''
        ],
        # Fila 7: Representante Legal | Ocupación
        [
            make_cell("Representante Legal", paciente.representante_legal),
            '',
            make_cell("Ocupación", paciente.ocupacion),
            ''
        ]
    ]

    col_widths = [(width - 2 * margin) * 0.4, (width - 2 * margin) * 0.1, (width - 2 * margin) * 0.25,
                  (width - 2 * margin) * 0.25]

    main_table = Table(data, colWidths=col_widths)
    main_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('SPAN', (0, 0), (1, 0)),  # Establecimiento/RUT
        ('SPAN', (2, 0), (3, 0)),  # Ficha/Pasaporte
        ('SPAN', (0, 1), (1, 1)),  # Nombre
        ('SPAN', (0, 2), (1, 2)),  # Nacimiento
        ('SPAN', (2, 2), (3, 2)),  # Fallecimiento
        ('SPAN', (0, 3), (1, 3)),  # Dirección
        ('SPAN', (0, 4), (1, 4)),  # Nombre Social
        ('SPAN', (0, 5), (1, 5)),  # Cónyuge
        ('SPAN', (2, 5), (3, 5)),  # Previsión
        ('SPAN', (0, 6), (1, 6)),  # Representante
        ('SPAN', (2, 6), (3, 6)),  # Ocupación
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))

    tw, th = main_table.wrap(0, 0)
    # 50px de margen superior aprox 1.76cm. El header ocupa espacio.
    main_table.drawOn(p, margin, top_margin - 2 * cm - th)

    p.showPage()
    p.save()

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response


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
    codigo_barras_base64 = generar_barcode_sticker_base64(numero_rut)

    context = {
        'paciente': paciente,
        'ficha': ficha,
        'codigo_barras_base64': codigo_barras_base64,
        'sticker_range': range(30)

    }

    return render(request, 'pdfs/formato_stickers.html', context)


def pdf_stickers_66_25(request, ficha_id=None, paciente_id=None):
    # Obtener el establecimiento del usuario
    establecimiento = getattr(request.user, 'establecimiento', None)

    # Lógica para obtener el paciente y la ficha
    if paciente_id:
        paciente = get_object_or_404(Paciente, id=paciente_id)
        ficha = Ficha.objects.filter(
            paciente=paciente,
            establecimiento=establecimiento
        ).first()
    elif ficha_id:
        ficha = get_object_or_404(Ficha, id=ficha_id)
        paciente = ficha.paciente
    else:
        raise Http404("Se requiere ficha o paciente")

    # Compatibilidad con plantillas: proporcionar atributos esperados
    if ficha:
        if not hasattr(ficha, 'numero_ficha'):
            ficha.numero_ficha = ficha.numero_ficha_sistema
    else:
        # Si no hay ficha para este establecimiento, crear un objeto dummy para el template
        ficha = SimpleNamespace(numero_ficha="S/F")

    # Generar código de barras basado en el RUT o código
    rut_paciente = getattr(paciente, 'rut', '') or ''
    numero_rut = obtener_numero_rut(rut_paciente)
    if not numero_rut:
        numero_rut = (getattr(paciente, 'codigo', '') or str(getattr(ficha, 'numero_ficha_sistema', '') or '')).strip()

    codigo_barras_base64 = generar_barcode_sticker_base64(numero_rut)

    # Obtener solo el primer nombre
    nombre = (getattr(paciente, 'nombre', '') or '').strip()
    partes = nombre.split()
    primer_nombre = partes[0] if partes else ''

    apellido_paterno = getattr(paciente, 'apellido_paterno', '') or ''
    apellido_materno = getattr(paciente, 'apellido_materno', '') or ''

    nombre_corto = f"{primer_nombre} {apellido_paterno} {apellido_materno}".strip()

    context = {
        'paciente': paciente,
        'ficha': ficha,
        'codigo_barras_base64': codigo_barras_base64,
        'nombre_corto': nombre_corto,
        'sticker_range': range(30)  # 3 columnas x 10 filas = 30 stickers
    }

    return render(request, 'pdfs/Etiquetas-Stick_Write-66x25.html', context)


def pdf_stickers_66_25_reportlab(request, ficha_id=None, paciente_id=None):
    from reportlab.lib.units import mm
    from reportlab.lib.pagesizes import letter

    # Obtener el establecimiento del usuario
    establecimiento = getattr(request.user, 'establecimiento', None)

    # Lógica para obtener el paciente y la ficha
    if paciente_id:
        paciente = get_object_or_404(Paciente, id=paciente_id)
        ficha = Ficha.objects.filter(
            paciente=paciente,
            establecimiento=establecimiento
        ).first()
    elif ficha_id:
        ficha = get_object_or_404(Ficha, id=ficha_id)
        paciente = ficha.paciente
    else:
        raise Http404("Se requiere ficha o paciente")

    # Preparar datos
    nombre = (getattr(paciente, 'nombre', '') or '').strip()
    partes = nombre.split()
    primer_nombre = partes[0] if partes else ''
    apellido_paterno = getattr(paciente, 'apellido_paterno', '') or ''
    apellido_materno = getattr(paciente, 'apellido_materno', '') or ''
    nombre_corto = f"{primer_nombre} {apellido_paterno} {apellido_materno}".strip().upper()

    fecha_nac = paciente.fecha_nacimiento.strftime("%d/%m/%Y") if paciente.fecha_nacimiento else ""
    comuna = paciente.comuna.nombre if hasattr(paciente, 'comuna') and paciente.comuna else ""
    info_nac = f"Nac: {fecha_nac}"
    if comuna:
        info_nac += f" - {comuna}"

    num_ficha = ""
    if ficha:
        n = getattr(ficha, 'numero_ficha', getattr(ficha, 'numero_ficha_sistema', 0))
        try:
            num_ficha = f"FICHA {int(n):04d}"
        except (ValueError, TypeError):
            num_ficha = f"FICHA {n}"

    rut_str = paciente.rut or "SIN RUT"

    # Generar código de barras basado en el RUT o código
    rut_paciente = getattr(paciente, 'rut', '') or ''
    numero_rut = obtener_numero_rut(rut_paciente)
    if not numero_rut:
        numero_rut = (getattr(paciente, 'codigo', '') or str(getattr(ficha, 'numero_ficha_sistema', '') or '')).strip()

    # Respuesta HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="stickers_66x25_{paciente.id}.pdf"'

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width_page, height_page = letter  # 215.9mm x 279.4mm

    # Medidas según HTML:
    # padding: 14mm 5mm 0 5mm;
    # grid-template-columns: repeat(3, 66mm);
    # grid-template-rows: repeat(10, 25mm);
    # gap: 0mm 2mm;

    col_width = 67 * mm
    row_height = 26 * mm
    gap_x = 5 * mm  # El usuario no menciona gap ahora, pero el ancho total 66.7*3 = 200.1mm cabe en 215.9mm
    margin_top = 10 * mm  # 1 centimetro
    margin_left = 5 * mm  # 0.5 centimetros
    
    # --- Variables de ajuste para el usuario ---
    # Si necesita mover all el bloque hacia arriba o abajo, puede ajustar margin_top.
    # El usuario pidió indicarle variables para ajustar milímetros/centímetros.
    # margin_top = 1.0 * cm  # Ejemplo en cm

    # En ReportLab el origen (0,0) es abajo a la izquierda.
    # Necesitamos calcular las posiciones Y desde arriba.
    
    for row in range(10):
        for col in range(3):
            # Coordenadas de la celda
            x = margin_left + col * (col_width + gap_x) # quitar los parentesis y el gap en caso de no requerir separacion
            y = height_page - margin_top - (row + 1) * row_height
            
            # --- Dibujar bordes del sticker (Solicitado por el usuario para ver separaciones) ---
            c.setDash(1, 2)  # Línea discontinua opcional, o c.setDash() para sólida
            c.setLineWidth(0.1)
            c.rect(x, y, col_width, row_height, stroke=0, fill=0) # el stroke son las lineas que se muestran en el fondo del sticker
            c.setDash()  # Restaurar a sólida para el resto del contenido
            
            # --- Dibujar contenido del sticker ---
            # El sticker mide 25.4mm de alto.
            # El último elemento (código de barras) debe tener un padding de 4mm para quedar justo al límite.
            # Si el código de barras tiene que quedar "al final bajo, justo en los 25mm",
            # y el alto es 25.4mm, calculamos desde el fondo de la celda.
            
            inner_x_center = x + col_width / 2.0
            
            # Calculamos las posiciones Y desde abajo hacia arriba
            # El usuario dice: "el último elemento el codigo de barra debe tener un padding de 4mm"
            # "el codigo de barra tiene que quedar al final bajo, justo en los 25mm" (asumo que se refiere a la base del sticker)
            
            bottom_padding = 1 * mm
            bc_height = 4 * mm
            bc_draw_y = y + bottom_padding
            
            # Espaciado entre elementos (ajustable para que quepan)
            inter_spacing = 1.0 * mm
            
            rut_y = bc_draw_y + bc_height + 0.5 * mm
            ficha_y = rut_y + 8 + inter_spacing
            info_y = ficha_y + 8 + inter_spacing
            nombre_y = info_y + 6.5 + inter_spacing

            # 5. Código de barras (Abajo con padding de 4mm)
            try:
                bc = code128.Code128(numero_rut, barHeight=bc_height, barWidth=1)
                bc_draw_x = inner_x_center - (bc.width / 2.0)
                bc.drawOn(c, bc_draw_x, bc_draw_y)
            except Exception:
                pass

            # 4. RUT (8pt)
            c.setFont("Helvetica", 8)
            c.drawCentredString(inner_x_center, rut_y, rut_str)

            # 3. Ficha (8pt Bold)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(inner_x_center, ficha_y, num_ficha)

            # 2. Info Nacimiento (6.5pt)
            c.setFont("Helvetica", 6.5)
            c.drawCentredString(inner_x_center, info_y, info_nac)

            # 1. Nombre (8pt Bold)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(inner_x_center, nombre_y, nombre_corto)

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response


def pdf_stickers_ejemplos(request):
    # Obtener los últimos 3 registros de fichas para el establecimiento del usuario logueado
    # Si el usuario no tiene establecimiento, se obtienen las últimas 3 de forma global (o manejar como en pdf_stickers)
    establecimiento = getattr(request.user, 'establecimiento', None)

    if establecimiento:
        fichas = Ficha.objects.filter(establecimiento=establecimiento).order_by('id')[:27]
    else:
        fichas = Ficha.objects.all().order_by('id')[:27]

    stickers_data = []

    for ficha in fichas:
        paciente = ficha.paciente

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
        codigo_barras_base64 = generar_barcode_sticker_base64_128(numero_rut)

        # Añadimos la data de cada ficha/sticker
        stickers_data.append({
            'paciente': paciente,
            'ficha': ficha,
            'codigo_barras_base64': codigo_barras_base64
        })

    context = {
        'stickers_data': stickers_data,
    }

    return render(request, 'pdfs/formato_stickers_ejemplos.html', context)


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


def generar_barcode_sticker_base64(codigo_paciente: str) -> str:
    buffer = BytesIO()
    try:
        from barcode.writer import ImageWriter
        writer = ImageWriter()
        mime_type = "image/png"
    except (ImportError, TypeError):
        from barcode.writer import SVGWriter
        writer = SVGWriter()
        mime_type = "image/svg+xml"

    codigo = barcode.get('code128', codigo_paciente, writer=writer)
    codigo.write(buffer, options={
        "module_width": 0.2,  # 🔹 barras un poco más anchas (largo)
        "module_height": 10.0,  # 🔹 mantenemos altura para que ocupe all el espacio
        "font_size": 0,  # 🔹 sin texto
        "quiet_zone": 0.1,  # 🔹 margen mínimo lateral del código
        "write_text": False,
        "margin": 0,  # 🔹 quitamos márgenes internos por defecto
    })

    base64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:{mime_type};base64,{base64_data}"


def generar_barcode_sticker_base64_128(valor):
    """
    Genera un código de barras Code128 en base64
    """
    if not valor:
        valor = "000000"

    buffer = BytesIO()

    # Forzar Code128
    code128 = barcode.get('code128', str(valor), writer=ImageWriter())

    code128.write(buffer, {
        'module_width': 0.2,  # Grosor barras
        'module_height': 10,  # Altura
        'quiet_zone': 2,
        'font_size': 8,
        'text_distance': 1,
        'write_text': True,
    })

    barcode_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{barcode_base64}"


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
            # Ordenar los movimientos por numero_ficha de mayor a menor
            movimientos_sorted = sorted(
                p['movimientos'],
                key=lambda x: int(x['numero_ficha']) if str(x['numero_ficha']).isdigit() else 0,
                reverse=True
            )
            profesionales_list.append({
                'nombre': str(p['obj']),
                'movimientos': movimientos_sorted
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


def pdf_movimientos_fichas_monologo_controlado(request):
    tipo = request.GET.get('tipo', 'salida')
    hora_inicio = request.GET.get('fecha_inicio')
    hora_termino = request.GET.get('fecha_termino')
    servicio_id = request.GET.get('servicio_clinico')
    profesional_id = request.GET.get('profesional')
    print(hora_inicio, hora_termino, servicio_id, profesional_id)

    establecimiento = getattr(request.user, 'establecimiento', None)
    if not establecimiento:
        raise Http404("El usuario no tiene un establecimiento asociado")

    # Definir campos dinámicos según tipo
    if tipo == 'entrada':
        titulo = "Entrega Fichas Monólogo – Entrada / Recepción"
        fecha_field = 'fecha_entrada'
        servicio_field = 'servicio_clinico_destino'
        profesional_field = 'profesional'
        usuario_field_str = 'usuario_entrada'
        etiqueta_usuario = "Recepcionado por"
        # Para entrada, deben tener fecha de recepción
        base_queryset = MovimientoMonologoControlado.objects.filter(
            establecimiento=establecimiento,
            fecha_entrada__isnull=False,
            status=True
        )
    elif tipo == 'transito':
        titulo = "Entrega Fichas Monólogo – En Tránsito"
        fecha_field = 'fecha_salida'
        servicio_field = 'servicio_clinico_destino'
        profesional_field = 'profesional'
        usuario_field_str = 'usuario_entrega'
        etiqueta_usuario = "Enviado por"
        # Tránsito: estado E (Enviado, no recibido)
        base_queryset = MovimientoMonologoControlado.objects.filter(
            establecimiento=establecimiento,
            estado='E',
            status=True
        )
    else:
        # Salida / Envío (Historial)
        titulo = "Entrega Fichas Monólogo – Salida / Envío"
        fecha_field = 'fecha_salida'
        servicio_field = 'servicio_clinico_destino'
        profesional_field = 'profesional'
        usuario_field_str = 'usuario_entrega'
        etiqueta_usuario = "Entregado por"
        base_queryset = MovimientoMonologoControlado.objects.filter(
            establecimiento=establecimiento,
            estado='E',
            status=True
        ).order_by('ficha__numero_ficha_sistema')

    filtros_aplicados = any([hora_inicio, hora_termino, servicio_id, profesional_id])

    # 1. SI HAY FILTROS: Imprimir exactamente lo que se muestra
    if filtros_aplicados:
        queryset = base_queryset.select_related(
            'rut_paciente',
            servicio_field,
            profesional_field
        )

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

        # Agrupación de datos según lo filtrado (sin límites especiales)
        datos_agrupados = []
        servicios_map = {}

        for m in queryset:
            s_obj = getattr(m, servicio_field)
            if not s_obj: continue
            s_id = s_obj.id

            if s_id not in servicios_map:
                servicios_map[s_id] = {
                    'obj': s_obj,
                    'profesionales_map': {},
                    'order': len(servicios_map)
                }

            s_data = servicios_map[s_id]
            p_obj = getattr(m, profesional_field)
            if not p_obj: continue
            p_id = p_obj.id

            if p_id not in s_data['profesionales_map']:
                s_data['profesionales_map'][p_id] = {
                    'obj': p_obj,
                    'movimientos': [],
                    'order': len(s_data['profesionales_map'])
                }

            p_data = s_data['profesionales_map'][p_id]
            usuario_responsable = getattr(m, usuario_field_str, 'N/A')

            p_data['movimientos'].append({
                'numero_ficha': m.numero_ficha,
                'rut_paciente': m.rut,
                'nombre_paciente': m.rut_paciente.nombre_completo if m.rut_paciente else 'N/A',
                'hora_movimiento': getattr(m, fecha_field),
                'usuario_responsable': m.usuario_entrega_id or 'N/A',
            })

        # Convertir mapas a listas ordenadas
        servicios_sorted = sorted(servicios_map.values(), key=lambda x: x['order'])
        for s in servicios_sorted:
            profs_sorted = sorted(s['profesionales_map'].values(), key=lambda x: x['order'])
            profesionales_list = []
            for p in profs_sorted:
                # Ordenar los movimientos por numero_ficha de mayor a menor
                movimientos_sorted = sorted(
                    p['movimientos'],
                    key=lambda x: int(x['numero_ficha']) if str(x['numero_ficha']).isdigit() else 0,
                    reverse=True
                )
                profesionales_list.append({
                    'nombre': str(p['obj']),
                    'movimientos': movimientos_sorted
                })
            datos_agrupados.append({
                'nombre': s['obj'].nombre,
                'profesionales': profesionales_list
            })

        subtitulo = "Resultados filtrados"
        if hora_inicio and hora_termino:
            subtitulo = f"Desde {hora_inicio} hasta {hora_termino}"
        elif hora_inicio:
            subtitulo = f"Desde {hora_inicio}"
        elif hora_termino:
            subtitulo = f"Hasta {hora_termino}"

    # 2. SI NO HAY FILTROS: Aplicar lógica de últimos servicios, profesionales y fichas
    else:
        # Usaremos una lógica de agrupación más robusta para evitar duplicados
        # cuando un servicio o profesional tiene múltiples movimientos con fechas distintas.
        limit_servicios = 30
        limit_profesionales = 2
        limit_fichas = 10

        # Obtener los movimientos más recientes del establecimiento
        queryset = base_queryset.select_related(
            'rut_paciente',
            servicio_field,
            profesional_field
        ).order_by(f'-{fecha_field}')

        datos_agrupados = []
        servicios_map = {}

        for m in queryset:
            s_obj = getattr(m, servicio_field)
            if not s_obj: continue
            s_id = s_obj.id

            if s_id not in servicios_map:
                if len(servicios_map) >= limit_servicios:
                    continue
                servicios_map[s_id] = {
                    'obj': s_obj,
                    'profesionales_map': {},
                    'order': len(servicios_map)
                }

            s_data = servicios_map[s_id]
            p_obj = getattr(m, profesional_field)
            if not p_obj: continue
            p_id = p_obj.id

            if p_id not in s_data['profesionales_map']:
                if len(s_data['profesionales_map']) >= limit_profesionales:
                    continue
                s_data['profesionales_map'][p_id] = {
                    'obj': p_obj,
                    'movimientos': [],
                    'order': len(s_data['profesionales_map'])
                }

            p_data = s_data['profesionales_map'][p_id]
            if len(p_data['movimientos']) >= limit_fichas:
                continue

            usuario_responsable = getattr(m, usuario_field_str, 'N/A')
            p_data['movimientos'].append({
                'numero_ficha': m.numero_ficha,
                'rut_paciente': m.rut,
                'nombre_paciente': m.rut_paciente.nombre_completo if m.rut_paciente else 'N/A',
                'hora_movimiento': getattr(m, fecha_field),
                'usuario_responsable': usuario_responsable or 'N/A',
            })

        # Convertir mapas a listas ordenadas
        servicios_sorted = sorted(servicios_map.values(), key=lambda x: x['order'])
        for s in servicios_sorted:
            profs_sorted = sorted(s['profesionales_map'].values(), key=lambda x: x['order'])
            profesionales_list = []
            for p in profs_sorted:
                # Ordenar los movimientos por numero_ficha de mayor a menor
                movimientos_sorted = sorted(
                    p['movimientos'],
                    key=lambda x: int(x['numero_ficha']) if str(x['numero_ficha']).isdigit() else 0,
                    reverse=True
                )
                profesionales_list.append({
                    'nombre': str(p['obj']),
                    'movimientos': movimientos_sorted
                })
            if profesionales_list:
                datos_agrupados.append({
                    'nombre': s['obj'].nombre,
                    'profesionales': profesionales_list
                })

        subtitulo = "Últimos movimientos registrados (Resumen)"

    context = {
        'titulo_movimiento': titulo,
        'subtitulo_filtros': subtitulo,
        'etiqueta_usuario': etiqueta_usuario,
        'servicios': datos_agrupados,
    }

    return render(request, 'pdfs/movimientos_fichas.html', context)
