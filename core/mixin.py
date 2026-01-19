from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse_lazy


class DataTableMixin:
    datatable_columns = []  # e.g. ['ID', 'Nombre', 'Codigo']
    datatable_search_fields = []  # e.g. ['nombre__icontains', 'codigo__icontains']
    datatable_order_fields = []  # e.g. ['id', None, 'nombre', 'codigo']
    model = None  # e.g. Comuna

    url_detail = None
    url_update = None
    url_delete = None

    permission_view = None
    permission_update = None
    permission_delete = None

    def get_base_queryset(self):
        qs = self.model.objects.all()
        # Auto-filtro por establecimiento si el middleware adjuntó request.establecimiento
        try:
            establecimiento = getattr(self.request, 'establecimiento', None)
        except Exception:
            establecimiento = None
        if establecimiento is None:
            return qs
        model_name = self.model.__name__ if self.model else ''
        # Filtrar para modelos que se relacionan con pacientes por establecimiento
        if model_name == 'Paciente':
            # Pacientes que tengan fichas en el establecimiento del usuario
            return qs.filter(fichas_pacientes__establecimiento=establecimiento).distinct()
        if model_name == 'Ficha':
            # Filtrar directamente por establecimiento en Ficha
            return qs.filter(establecimiento=establecimiento)
        if model_name == 'IngresoPaciente':
            return qs.filter(establecimiento=establecimiento)
        # Para otros modelos no se aplica filtro aquí por defecto
        return qs

    def render_row(self, obj):
        return {
            'ID': obj.id,
            'Nombre': getattr(obj, 'nombre', ''),
            'Codigo': getattr(obj, 'codigo', ''),
        }

    def get_actions(self, obj):
        """
        Devuelve el HTML de los botones de acciones, según permisos definidos en la clase hija.
        """
        user = self.request.user
        actions = []

        if self.url_detail:
            # Check if url_detail is 'paciente_view_param' to use 'paciente_id' instead of 'pk'
            detail_kwargs = {'pk': obj.pk}
            if self.url_detail == 'paciente_view_param':
                detail_kwargs = {'paciente_id': obj.pk}

            actions.append(f"""
                <a href="{reverse_lazy(f'{self.url_detail}', kwargs=detail_kwargs)}"
                   class="btn p-1 btn-sm btn-secondary view-btn" title="Ver detalle">
                   <i class="fas fa-search"></i></a>
            """)

        if self.url_update:
            # Check if url_update is 'paciente_view_param' to use 'paciente_id' instead of 'pk'
            update_kwargs = {'pk': obj.pk}
            if self.url_update == 'paciente_view_param':
                update_kwargs = {'paciente_id': obj.pk}

            actions.append(f"""
                <a href="{reverse_lazy(f'{self.url_update}', kwargs=update_kwargs)}"
                   class="btn p-1 btn-sm btn-info" title="Editar">
                   <i class="fas fa-edit"></i></a>
            """)

        return ''.join(actions)

    def filter_queryset(self, qs, search_value):
        """
        Filtra el queryset según los campos de búsqueda definidos.
        """
        if search_value and self.datatable_search_fields:
            q = Q()
            for field in self.datatable_search_fields:
                q |= Q(**{field: search_value})
            qs = qs.filter(q)
        return qs

    def get_datatable_response(self, request):
        qs = self.get_base_queryset()

        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 100))
        search_value = request.GET.get('search[value]', '').strip()

        qs = self.filter_queryset(qs, search_value)
        records_total = self.get_base_queryset().count()
        records_filtered = qs.count()

        # Ordenamiento
        try:
            order_col = int(request.GET.get('order[0][column]', 0))
        except (TypeError, ValueError):
            order_col = 0
        order_dir = request.GET.get('order[0][dir]', 'asc')

        order_field = (
            self.datatable_order_fields[order_col]
            if 0 <= order_col < len(self.datatable_order_fields)
            else 'id'
        )
        if order_field:
            if order_dir == 'desc':
                order_field = f'-{order_field}'
            qs = qs.order_by(order_field)

        qs_page = qs[start:start + length]

        data = []
        for obj in qs_page:
            row = self.render_row(obj)
            row['actions'] = self.get_actions(obj)
            data.append(row)

        return JsonResponse({
            'draw': draw,
            'recordsTotal': records_total,
            'recordsFiltered': records_filtered,
            'data': data,
        })
