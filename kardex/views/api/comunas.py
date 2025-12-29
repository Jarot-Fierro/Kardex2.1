# serializers.py
from rest_framework import serializers, viewsets

from kardex.models import Comuna


class ComunaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comuna
        fields = ["id", "nombre"]


# views.py
class ComunaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Comuna.objects.order_by("nombre")
    serializer_class = ComunaSerializer
