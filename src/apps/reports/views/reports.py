from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

from rest_framework.response import Response

from apps.reports.filters.report_region import ReportFilter
from apps.reports.models import Report, Plant, ReportItem, StatementColumn
from apps.reports.permissions import CanCreateReport, CanUpdateReport
from apps.reports.permissions.check_delete_report import CanDeleteReport
from apps.reports.permissions.check_list_report import CanListReport
from apps.reports.serializers.reports import (
    ReportListSerializer,
    ReportCreateSerializer,
    ReportUpdateSerializer, ReportDetailSerializer,
)
from apps.base.views import (
    CustomListAPIView,
    CustomCreateAPIView, CustomRetrieveAPIView, CustomDestroyAPIView, CustomRetrieveUpdateAPIView,
)
from apps.logs.drf_mixins import DRFHistoryMixin
from apps.utils.translation import get_lang_code


@extend_schema(
    tags=["Reports"],
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
class ReportListAPIView(CustomListAPIView):
    pagination_class = None
    serializer_class = ReportListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReportFilter

    def _base_queryset(self):
        """
        Faqat role/filter uchun bazaviy QS.
        Bu yerda prefetch yo‘q -> statement_ids olish arzon.
        """
        user = self.request.user
        if not user.is_authenticated:
            return Report.objects.none()

        qs = Report.objects.filter(statement__parent__isnull=False)

        # umumiy reportlar list endpointda ko‘rinmasin
        qs = qs.filter(is_general=False, is_individual_general=False, is_republic=False)

        if user.is_superuser:
            return qs

        if user.role in ['tashkilot_hodimi', 'hududiy_boshqarma', 'tashkilot_rahbari']:
            return qs.filter(organization=user.organization)

        if user.role == 'bolim_admin':
            return qs.filter(statement__parent_id=user.statement.id)

        return Report.objects.none()

    def get_queryset(self):
        """
        Final QS: select_related + prefetch_related faqat shu yerda.
        """
        qs = self._base_queryset()

        # statement_ids - context uchun 1 marta
        if not hasattr(self, "_statement_ids"):
            self._statement_ids = list(qs.values_list("statement_id", flat=True).distinct())

        qs = (
            qs.select_related(
                "organization",
                "organization__republic",
                "statement",
                "statement__parent",
                "deadline",
                "sent_by",
                "sent_by_org",
            )
            .prefetch_related(
                Prefetch(
                    "report_items",
                    queryset=(
                        ReportItem.objects
                        .select_related("statement_column", "statement_column__parent")
                        .prefetch_related("inners")  # inners ham prefetched
                    )
                )
            )
            .order_by("-created_at")
        )
        return qs

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response([])
        return super().list(request, *args, **kwargs)

    def get_serializer_context(self):
        """
        MUHIM: get_queryset() chaqirmaymiz!
        Aks holda barcha querylar yana 1 marta aylanadi.
        """
        context = super().get_serializer_context()

        lang = self.request.query_params.get("lang", "uz").lower()
        if lang not in ("uz", "ru"):
            lang = "uz"

        context["lang"] = lang
        context["lang"] = lang

        # Plant map: tezkor (1 query)
        context["plant_map"] = {
            str(pid): name for pid, name in Plant.objects.values_list("id", "name")
        }

        # StatementColumn preload: statement_ids oldindan hisoblangan
        statement_ids = getattr(self, "_statement_ids", [])
        if statement_ids:
            cols = (
                StatementColumn.objects
                .filter(statement_id__in=statement_ids)
                .select_related("parent")
                .only(
                    "id", "parent_id", "ordering",
                    "title_uz", "title_ru",
                    "is_organization", "statement_id"
                )
            )
            columns_by_statement_id = {}
            for c in cols:
                columns_by_statement_id.setdefault(str(c.statement_id), []).append(c)

            context["columns_by_statement_id"] = columns_by_statement_id
        else:
            context["columns_by_statement_id"] = {}

        return context


@extend_schema(tags=["Reports"])
class ReportCreateAPIView(DRFHistoryMixin,CustomCreateAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportCreateSerializer
    permission_classes = (CanCreateReport,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        created_reports = serializer.save()

        list_data = ReportListSerializer(
            created_reports, many=True, context=self.get_serializer_context()
        ).data


        return Response(list_data, status=201)


@extend_schema(tags=["Reports"])
class ReportDeleteAPIView(DRFHistoryMixin,CustomDestroyAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportDetailSerializer
    permission_classes = (CanDeleteReport,)
    lookup_field = 'id'


@extend_schema(tags=["Reports"])
class ReportRetrieveAPIView(CustomRetrieveAPIView):
    queryset = Report.objects.select_related(
        'statement',
        'deadline__statement',
        'deadline',
        'organization'
    ).prefetch_related(
        'report_items__inners',
        'report_items__statement_column',
    )
    serializer_class = ReportDetailSerializer
    lookup_field = 'id'


@extend_schema(tags=["Reports"])
class ReportUpdateAPIView(DRFHistoryMixin,CustomRetrieveUpdateAPIView):
    queryset = Report.objects.select_related(
        'statement',
        'deadline__statement',
        'deadline',
        'organization',
    ).prefetch_related(
        'report_items__inners',
        'report_items__statement_column',
    ).distinct().order_by('-created_at')
    serializer_class = ReportUpdateSerializer
    lookup_field = 'id'
    # permission_classes = (CanUpdateReport,)

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return ReportUpdateSerializer
        return ReportDetailSerializer