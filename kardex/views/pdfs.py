import base64
from io import BytesIO
from types import SimpleNamespace

import barcode
from barcode.writer import ImageWriter
from django.contrib.auth.decorators import permission_required
from django.http import Http404
from django.shortcuts import render, get_object_or_404

from kardex.models import Ficha
from kardex.models import Paciente


@permission_required('kardex.view_paciente', raise_exception=True)
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


@permission_required('kardex.view_paciente', raise_exception=True)
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
        'sticker_range': range(24)

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
    codigo = barcode.get('code128', codigo_paciente, writer=ImageWriter())
    codigo.write(buffer, options={
        "module_height": 10.0,
        "font_size": 10,
        "quiet_zone": 1,
        "write_text": False,
    })

    base64_img = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{base64_img}"
