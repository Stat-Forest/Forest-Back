from django.db.models import Prefetch
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.reports.models import Report, Plant, StatementColumn, ReportItem, ReportItemInner
from apps.base.views import CustomListAPIView, CustomRetrieveAPIView
from apps.reports.serializers.plant import UniversalPlantReportCreateSerializer, PlantReportUpdateSerializer, \
    PlantReportUpdateReadSerializer
from apps.reports.serializers.plant.plant_report_delete import PlantReportDeleteSerializer
from apps.reports.serializers.plant.plant_report_list import PlantReportListSerializer
from apps.logs.drf_mixins import DRFHistoryMixin
from apps.reports.services.pagination import ReportPagination
from apps.reports.permissions.report_scope import ReportScopedQuerysetMixin, scope_reports_for_user, CanEditReportData
from apps.reports.permissions.check_create_report import CanCreateReport


@extend_schema(tags=["Plant-Reports"])
class UniversalPlantReportCreateAPIView(DRFHistoryMixin, APIView):
    # Hisobotni faqat tashkilot hodimi (va super_admin) yaratadi — oddiy hisobot bilan bir xil (audit N1)
    permission_classes = (CanCreateReport,)

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
    pagination_class = ReportPagination
    serializer_class = PlantReportListSerializer

    def get_queryset(self):
        qs = scope_reports_for_user(Report.objects.filter(is_plant_based=True), self.request.user)
        # Ustunlar faqat shu ro'yxatdagi statement'lar uchun yuklanadi
        self._statement_ids = list(qs.values_list("statement_id", flat=True).distinct())
        return (
            qs
            .select_related(
                "organization",
                "statement",
                "deadline",
                "sent_by",
                "sent_by_org",
            )
            .prefetch_related(
                "report_items__statement_column__parent",
                "report_items__inners__plant",
            )
            .order_by("-created_at")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()

        lang = self.request.query_params.get("lang", "uz").lower()
        context["lang"] = lang if lang in ("uz", "ru") else "uz"

        # Ro'yxatdagi statement'larning ustunlari bir marta olinadi (ilgari butun jadval)
        statement_ids = getattr(self, "_statement_ids", [])
        columns = StatementColumn.objects.filter(statement_id__in=statement_ids).select_related("parent").only(
            "id",
            "statement_id",
            "parent_id",
            "ordering",
            "title",
            "title_uz",
            "title_ru",
            "is_organization",
            "status_plan",
            "is_user_input",
        )
        context["statement_columns"] = {str(c.id): c for c in columns}

        return context


@extend_schema(tags=["Plant-Reports"])
class PlantUpdateReportAPIView(DRFHistoryMixin, RetrieveUpdateAPIView):
    """
    Plant-based reportlar uchun GET/UPDATE endpoint.
    Daromad bo'lsa quarter workflow ishlaydi,
    qolgan statementlar esa eski update oqimida qoladi.
    """
    # Faqat EDITOR_ROLES va faqat saved/cancelled (joriy chorak) holatda — oddiy
    # hisobot update'i bilan bir xil (audit N3: ilgari ACCEPTED ham o'zgartirilardi)
    permission_classes = (CanEditReportData,)

    def get_queryset(self):
        base_qs = scope_reports_for_user(
            Report.objects.filter(is_plant_based=True), self.request.user
        )

        if self.request.method == "GET":
            return base_qs.select_related(
                "statement",
                "deadline",
                "organization",
            ).prefetch_related(
                Prefetch(
                    "report_items",
                    queryset=ReportItem.objects.select_related(
                        "statement_column"
                    ).prefetch_related(
                        Prefetch(
                            "inners",
                            queryset=ReportItemInner.objects.select_related("plant")
                        )
                    )
                )
            )

        # UPDATE uchun yengilroq queryset kifoya
        return base_qs.select_related(
            "statement",
            "deadline",
            "organization",
        )

    def get_serializer_class(self):
        if self.request.method == "GET":
            return PlantReportUpdateReadSerializer
        return PlantReportUpdateSerializer


@extend_schema(tags=["Plant-Reports"])
class PlantDetailReportAPIView(ReportScopedQuerysetMixin, CustomRetrieveAPIView):
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
