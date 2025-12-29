from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse_lazy


class DataTableMixin:
    model = None

    datatable_columns = []
    datatable_search_fields = []
    datatable_order_fields = []
    datatable_select_related = []
    datatable_prefetch_related = []
    datatable_only = []  # campos que sí cargo
    datatable_defer = []  # campos que NO cargo (pesados, blobs, html, etc.)

    url_detail = url_update = url_delete = None
    permission_view = permission_update = permission_delete = None

    # -------------------- QUERY BASE EFICIENTE --------------------
    def get_base_queryset(self):
        qs = self.model.objects.all()

        if self.datatable_select_related:
            qs = qs.select_related(*self.datatable_select_related)

        if self.datatable_prefetch_related:
            qs = qs.prefetch_related(*self.datatable_prefetch_related)

        if self.datatable_only:
            qs = qs.only(*self.datatable_only)

        if self.datatable_defer:
            qs = qs.defer(*self.datatable_defer)

        # filtro opcional por establecimiento
        establecimiento = getattr(self.request, 'establecimiento', None)
        if not establecimiento:
            return qs

        model = self.model.__name__
        if model == 'Paciente':
            return qs.filter(fichas_pacientes__establecimiento=establecimiento).distinct()
        if model in ('Ficha', 'IngresoPaciente'):
            return qs.filter(establecimiento=establecimiento)

        return qs

    # -------------------- FORMATTER DE FILA --------------------
    def render_row(self, obj):
        return {col: getattr(obj, col.lower(), '') for col in self.datatable_columns}

    # -------------------- BOTONES --------------------
    def get_actions(self, obj):
        user = self.request.user
        actions = []

        def btn(url, icon, color, permiso):
            if permiso and user.has_perm(permiso):
                return f'<a href="{reverse_lazy(url, kwargs={"pk": obj.pk})}" class="btn p-1 btn-sm btn-{color}"><i class="fas {icon}"></i></a>'
            return ''

        actions.append(btn(self.url_detail, 'fa-search', 'secondary', self.permission_view))
        actions.append(btn(self.url_update, 'fa-edit', 'info', self.permission_update))
        actions.append(btn(self.url_delete, 'fa-trash', 'danger', self.permission_delete))

        return ''.join(actions)

    # -------------------- BUSQUEDA --------------------
    def filter_queryset(self, qs, search_value):
        if search_value and self.datatable_search_fields:
            q = Q()
            for field in self.datatable_search_fields:
                q |= Q(**{field: search_value})
            return qs.filter(q)
        return qs

    # -------------------- RESPUESTA DATATABLE --------------------
    def get_datatable_response(self, request):
        qs = self.get_base_queryset()  # ahora cacheado y no se repite

        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 100))
        search = request.GET.get('search[value]', '').strip()

        # FILTRO
        qs_filtered = self.filter_queryset(qs, search)

        records_total = qs.count()
        records_filtered = qs_filtered.count() if search else records_total

        # ORDENAMIENTO
        order_col = int(request.GET.get('order[0][column]', 0))
        order_dir = request.GET.get('order[0][dir]', 'asc')
        if 0 <= order_col < len(self.datatable_order_fields):
            field = self.datatable_order_fields[order_col]
            if field:
                qs_filtered = qs_filtered.order_by(f'-{field}' if order_dir == 'desc' else field)

        # PAGINACIÓN
        qs_page = qs_filtered[start:start + length]

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
