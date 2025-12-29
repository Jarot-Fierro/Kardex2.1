from django.core.exceptions import PermissionDenied
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from kardex.models import Paciente, Ficha
from kardex.models.paciente_ficha import VistaFichaPaciente


class VistaFichaPacienteSerializer(serializers.Serializer):
    # -------- FICHA -------
    ficha_id = serializers.IntegerField()
    numero_ficha_sistema = serializers.IntegerField()
    numero_ficha_tarjeta = serializers.IntegerField(allow_null=True)

    pasivado = serializers.BooleanField()
    observacion = serializers.CharField(allow_null=True)
    fecha_creacion_anterior = serializers.DateTimeField(allow_null=True)

    profesional_id = serializers.IntegerField(allow_null=True)
    sector_id = serializers.IntegerField(allow_null=True)
    usuario_id = serializers.IntegerField(allow_null=True)

    # -------- ESTABLECIMIENTO -------
    establecimiento_id = serializers.IntegerField()
    establecimiento_nombre = serializers.CharField()

    # -------- PACIENTE -------
    paciente_id = serializers.IntegerField()
    paciente_codigo = serializers.CharField()

    rut = serializers.CharField()
    nip = serializers.CharField(allow_null=True)

    nombre = serializers.CharField()
    apellido_paterno = serializers.CharField()
    apellido_materno = serializers.CharField()

    nombre_social = serializers.CharField(allow_null=True)
    genero = serializers.CharField()

    fecha_nacimiento = serializers.DateField(allow_null=True)
    sexo = serializers.CharField()
    estado_civil = serializers.CharField()

    rut_madre = serializers.CharField(allow_null=True)
    nombres_padre = serializers.CharField(allow_null=True)
    nombres_madre = serializers.CharField(allow_null=True)
    nombre_pareja = serializers.CharField(allow_null=True)
    representante_legal = serializers.CharField(allow_null=True)

    pueblo_indigena = serializers.BooleanField()
    recien_nacido = serializers.BooleanField()
    extranjero = serializers.BooleanField()
    fallecido = serializers.BooleanField()

    fecha_fallecimiento = serializers.DateField(allow_null=True)
    alergico_a = serializers.CharField(allow_null=True)

    direccion = serializers.CharField(allow_null=True)
    sin_telefono = serializers.BooleanField()

    numero_telefono1 = serializers.CharField(allow_null=True)
    numero_telefono2 = serializers.CharField(allow_null=True)

    ocupacion = serializers.CharField(allow_null=True)

    paciente_comuna_id = serializers.IntegerField()
    prevision_id = serializers.IntegerField(allow_null=True)

    pasaporte = serializers.CharField(allow_null=True)
    rut_responsable_temporal = serializers.CharField(allow_null=True)

    usar_rut_madre_como_responsable = serializers.BooleanField()


class PacienteFichaViewSet(ViewSet):
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    queryset = Paciente.objects.all()

    # =================================================
    # CONSULTA
    # =================================================
    def list(self, request):

        if not request.user.has_perm('kardex.view_paciente'):
            raise PermissionDenied("No tienes permiso para consultar pacientes.")

        rut = request.GET.get("rut")
        numero_ficha = request.GET.get("numero_ficha")
        establecimiento_id = request.user.establecimiento_id

        if not rut and not numero_ficha:
            return Response({"error": "Debe indicar RUT o número de ficha."}, status=400)

        vista = None

        # Buscar por RUT
        if rut:
            rut = rut.strip().lower()
            vista = VistaFichaPaciente.objects.filter(
                rut=rut,
                establecimiento_id=establecimiento_id
            ).first()

        # Buscar por número de ficha
        elif numero_ficha:
            try:
                numero_ficha = int(numero_ficha)
            except ValueError:
                return Response({"error": "Número de ficha inválido."}, status=400)

            vista = VistaFichaPaciente.objects.filter(
                numero_ficha_sistema=numero_ficha,
                establecimiento_id=establecimiento_id
            ).first()

        # ============ CASO 1: EXISTE FICHA ============
        if vista:
            serializer = VistaFichaPacienteSerializer(vista)
            return Response({
                "exists": True,
                "has_ficha": True,
                "data": serializer.data
            })

        # ============ CASO 2: EXISTE PACIENTE SIN FICHA ============
        if rut:
            paciente = Paciente.objects.filter(rut=rut).first()
            if paciente:
                data_paciente = {
                    "paciente_id": paciente.id,
                    "codigo": getattr(paciente, "codigo", "") or "",
                    "rut": paciente.rut or "",
                    "nip": paciente.nip or "",
                    "nombre": paciente.nombre or "",
                    "apellido_paterno": paciente.apellido_paterno or "",
                    "apellido_materno": paciente.apellido_materno or "",
                    "rut_madre": paciente.rut_madre or "",
                    "rut_responsable_temporal": paciente.rut_responsable_temporal or "",

                    "pueblo_indigena": bool(paciente.pueblo_indigena),
                    "usar_rut_madre_como_responsable": bool(
                        paciente.usar_rut_madre_como_responsable
                    ),

                    "pasaporte": paciente.pasaporte or "",
                    "nombre_social": paciente.nombre_social or "",
                    "genero": paciente.genero or "",

                    "fecha_nacimiento": paciente.fecha_nacimiento,
                    "sexo": paciente.sexo or "",
                    "estado_civil": paciente.estado_civil or "",

                    "nombres_padre": paciente.nombres_padre or "",
                    "nombres_madre": paciente.nombres_madre or "",
                    "nombre_pareja": paciente.nombre_pareja or "",
                    "representante_legal": paciente.representante_legal or "",

                    "direccion": paciente.direccion or "",
                    "sin_telefono": bool(paciente.sin_telefono),

                    "numero_telefono1": paciente.numero_telefono1 or "",
                    "numero_telefono2": paciente.numero_telefono2 or "",

                    "ocupacion": paciente.ocupacion or "",

                    "recien_nacido": bool(paciente.recien_nacido),
                    "extranjero": bool(paciente.extranjero),
                    "fallecido": bool(paciente.fallecido),
                    "fecha_fallecimiento": paciente.fecha_fallecimiento,

                    "alergico_a": paciente.alergico_a or "",

                    "paciente_comuna_id": paciente.comuna_id,
                    "prevision_id": paciente.prevision_id,

                    "usuario_id": paciente.usuario_id,
                    "usuario_anterior_id": paciente.usuario_anterior_id,
                }

                return Response({
                    "exists": True,
                    "has_ficha": False,
                    **data_paciente
                })

        # ============ CASO 3: NO EXISTE ============
        return Response({"exists": False, "has_ficha": False})

    # =================================================
    # CREAR
    # =================================================
    def create(self, request):

        if not request.user.has_perm('kardex.add_paciente'):
            raise PermissionDenied("No tienes permiso para crear fichas.")

        establecimiento = request.user.establecimiento

        rut = request.data.get("rut")
        if not rut:
            return Response({"error": "RUT requerido."}, status=400)

        paciente, creado = Paciente.objects.get_or_create(
            rut=rut,
            defaults={
                "nombre": request.data.get("nombre"),
                "apellido_paterno": request.data.get("apellido_paterno"),
                "apellido_materno": request.data.get("apellido_materno"),
            }
        )

        if Ficha.objects.filter(
                paciente=paciente,
                establecimiento=establecimiento
        ).exists():
            return Response(
                {"error": "El paciente ya tiene ficha en este establecimiento."},
                status=409
            )

        ficha = Ficha.objects.create(
            paciente=paciente,
            establecimiento=establecimiento,
            usuario=request.user
        )

        return Response({
            "success": True,
            "ficha_id": ficha.id,
            "numero_ficha": ficha.numero_ficha_sistema,
        }, status=status.HTTP_201_CREATED)

    # =================================================
    # ACTUALIZAR
    # =================================================
    def update(self, request, pk=None):

        if not request.user.has_perm('kardex.change_paciente'):
            raise PermissionDenied("No tienes permiso para modificar pacientes.")

        try:
            paciente = Paciente.objects.get(pk=pk)
        except Paciente.DoesNotExist:
            return Response(
                {"error": "Paciente no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        CAMPOS_EDITABLES = [
            "nombre",
            "apellido_paterno",
            "apellido_materno",
            "nombre_social",
            "genero",
            "sexo",
            "estado_civil",
            "direccion",
            "ocupacion"
        ]

        for campo in CAMPOS_EDITABLES:
            if campo in request.data:
                setattr(paciente, campo, request.data[campo])

        paciente.save()

        return Response({"success": True})
