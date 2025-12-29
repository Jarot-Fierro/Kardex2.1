# serializers.py
from rest_framework import serializers, viewsets

from kardex.models import Sector


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ["id", "color"]


# views.py
class SectorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sector.objects.order_by("color")
    serializer_class = SectorSerializer
