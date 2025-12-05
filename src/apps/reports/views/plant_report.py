from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.reports.models import Report, Plant
from apps.base.views import CustomListAPIView, CustomRetrieveAPIView, CustomUpdateAPIView
from apps.reports.serializers.plant import UniversalPlantReportCreateSerializer, PlantReportUpdateSerializer
from apps.reports.serializers.plant.plant_report_delete import PlantReportDeleteSerializer
from apps.reports.serializers.plant.plant_report_list import PlantReportListSerializer
from apps.logs.drf_mixins import DRFHistoryMixin


@extend_schema(tags=["Plant-Reports"])
class UniversalPlantReportCreateAPIView(DRFHistoryMixin, APIView):
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


@extend_schema(
    tags=["Plant-Reports"],
    parameters=[
        OpenApiParameter(
            name="lang",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Tilni belgilang: uz yoki ru",
            required=False,
            enum=["uz", "ru"]
        )
    ]
)
class PlantListReportAPIView(CustomListAPIView):
    serializer_class = PlantReportListSerializer

    def get_queryset(self):
        return Report.objects.filter(is_plant_based=True).select_related(
            "organization", "statement", "deadline"
        ).prefetch_related(
            "report_items__statement_column__parent",
            "report_items__inners__plant"
        ).order_by("-created_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz")
        context["lang"] = lang
        plant_qs = Plant.objects.only("id", "name")
        context["plant_map"] = {str(p.id): p.name for p in plant_qs}
        return context


@extend_schema(tags=["Plant-Reports"])
class PlantUpdateReportAPIView(DRFHistoryMixin, CustomUpdateAPIView):
    serializer_class = PlantReportUpdateSerializer
    queryset = Report.objects.filter(is_plant_based=True, is_report=True)


@extend_schema(tags=["Plant-Reports"])
class PlantDetailReportAPIView(CustomRetrieveAPIView):
    queryset = Report.objects.filter(is_plant_based=True).select_related(
        "organization", "statement", "deadline"
    ).prefetch_related("report_items__statement_column__parent",
                       "report_items__inners__plant")

    serializer_class = PlantReportListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz")
        context["lang"] = lang
        plant_qs = Plant.objects.only("id", "name")
        context["plant_map"] = {str(p.id): p.name for p in plant_qs}
        return context


@extend_schema(tags=["Plant-Reports"])
class PlantReportDeleteAPIView(APIView):
    def delete(self, request, pk):
        serializer = PlantReportDeleteSerializer(
            data={"report_id": pk},
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.delete()
        return Response(result, status=200)
