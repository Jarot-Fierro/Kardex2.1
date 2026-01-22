from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse

from personas.models.pacientes import Paciente


@login_required
def buscar_pacientes_api(request):
    """
    API genérica para buscar pacientes con paginación.
    Soporta búsqueda por nombre, apellido, rut y código.
    """
    query = request.GET.get('search', '').strip()
    page_number = request.GET.get('page', 1)
    page_size = 40

    pacientes_qs = Paciente.objects.filter(status=True)

    if query:
        # Limpiar RUT si es necesario para la búsqueda
        query_clean = query.replace('.', '').replace('-', '').upper()

        pacientes_qs = pacientes_qs.filter(
            Q(nombre__icontains=query) |
            Q(apellido_paterno__icontains=query) |
            Q(apellido_materno__icontains=query) |
            Q(rut__icontains=query) |
            Q(rut__icontains=query_clean) |
            Q(codigo__icontains=query)
        ).distinct()

    # Ordenar para que la paginación sea consistente
    pacientes_qs = pacientes_qs.order_by('apellido_paterno', 'apellido_materno', 'nombre')

    paginator = Paginator(pacientes_qs, page_size)
    page_obj = paginator.get_page(page_number)

    results = []
    for p in page_obj:
        nombre_completo = f"{p.nombre} {p.apellido_paterno} {p.apellido_materno}".strip()
        text = f"{nombre_completo} ({p.rut or p.codigo})"
        results.append({
            'id': p.id,
            'text': text
        })

    return JsonResponse({
        'results': results,
        'pagination': {
            'more': page_obj.has_next()
        }
    })
