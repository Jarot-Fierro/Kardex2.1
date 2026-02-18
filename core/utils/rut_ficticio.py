import random
import re
from core.validations import format_rut, validate_rut

def calcular_dv_rut(cuerpo):
    """
    Calcula el dígito verificador de un RUT dado su cuerpo (entero o string).
    Basado en el algoritmo del módulo 11.
    """
    cuerpo = str(cuerpo)
    reversed_digits = map(int, reversed(cuerpo))
    factors = [2, 3, 4, 5, 6, 7]
    
    total = 0
    for i, digit in enumerate(reversed_digits):
        total += digit * factors[i % len(factors)]
    
    remainder = total % 11
    expected = 11 - remainder
    
    if expected == 11:
        return "0"
    elif expected == 10:
        return "K"
    else:
        return str(expected)

def generar_rut_ficticio_unico(model_class, field_name='rut', retries=50):
    """
    Genera un RUT ficticio único en el rango 90.000.000 - 99.999.999.
    Verifica que no exista en la base de datos para la clase de modelo y campo dados.
    """
    for _ in range(retries):
        cuerpo = random.randint(90000000, 99999999)
        dv = calcular_dv_rut(cuerpo)
        rut_generado = f"{cuerpo}-{dv}"
        rut_formateado = format_rut(rut_generado)
        
        # Verificar unicidad
        if not model_class.objects.filter(**{field_name: rut_formateado}).exists():
            return rut_formateado
            
    return None

def es_rut_recien_nacido(rut):
    """
    Determina si un RUT pertenece al rango de recién nacidos ficticios (>= 90.000.000).
    """
    if not rut:
        return False
    # Limpiar y extraer el cuerpo
    rut_num = re.sub(r'[^\d]', '', rut.split('-')[0] if '-' in rut else rut)
    return rut_num.isdigit() and int(rut_num) >= 90000000
