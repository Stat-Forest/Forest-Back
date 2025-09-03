from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated

from apps.reports.serializers.plant.plant_create import PlantBasedReportCreateSerializer


class PlantBasedReportCreateAPIView(CreateAPIView):
    serializer_class = PlantBasedReportCreateSerializer
    permission_classes = [IsAuthenticated]


