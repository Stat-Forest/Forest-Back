from rest_framework.views import APIView
from rest_framework.response import Response

from apps.reports.models import Report
from apps.base.views import CustomListAPIView
from apps.reports.serializers.plant import UniversalPlantReportCreateSerializer
from apps.reports.serializers.plant.plant_report_list import PlantReportListSerializer


class UniversalPlantReportCreateAPIView(APIView):
    def post(self, request):
        serializer = UniversalPlantReportCreateSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        reports = serializer.save()
        response_serializer = PlantReportListSerializer(
            reports,
            many=True,
            context={"request": request}
        )
        return Response(response_serializer.data, status=201)


class PlantListReportAPIView(CustomListAPIView):
    serializer_class = PlantReportListSerializer

    def get_queryset(self):
        return Report.objects.filter(is_plant_based=True).select_related(
            "organization", "statement", "deadline"
        ).prefetch_related(
            "report_items__statement_column__parent",
            "report_items__inners__plant"
        ).order_by("-created_at")
