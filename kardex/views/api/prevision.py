# serializers.py
from rest_framework import serializers, viewsets

from kardex.models import Prevision


class PrevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prevision
        fields = ["id", "nombre"]


# views.py
class PrevisionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Prevision.objects.order_by("nombre")
    serializer_class = PrevisionSerializer
