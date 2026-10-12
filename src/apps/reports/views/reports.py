from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.pagination import LimitOffsetPagination

from rest_framework.response import Response

from apps.reports.permissions import CanCreateReport
from apps.reports.filters.report_region import ReportFilter
from apps.reports.permissions.check_delete_report import CanDeleteReport
from apps.reports.permissions.report_scope import ReportScopedQuerysetMixin, CanEditReportData
from apps.reports.models import Report, ReportItem, StatementColumn
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
from apps.reports.services.pagination import ReportPagination
from apps.reports.services.report_items_loader import load_report_items


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
    pagination_class = ReportPagination

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

        # TASHKILOT_HODIMI / TASHKILOT_RAHBARI
        if user.role in ['tashkilot_hodimi', 'tashkilot_rahbari']:
            return qs.filter(organization=user.organization)

        # BOLIM_ADMIN
        if user.role == 'bolim_admin':
            if not user.statement_id:
                return qs.none()
            return qs.filter(statement__parent_id=user.statement_id)

        # IJARA BILLING ROLLARI — kadastr bo'limi, tashkilot doirasi
        if user.role in ('billing_user', 'billing_super'):
            from apps.reports.permissions.report_scope import scope_reports_for_billing_role
            return scope_reports_for_billing_role(qs, user)

        # HUDUDIY_BOSHQARMA
        if user.role == 'hududiy_boshqarma':
            org_regions = list(user.region_user_orgs.values_list('region', flat=True).distinct())
            if org_regions:
                return qs.filter(organization__region__in=org_regions)
            return qs.none()

        return Report.objects.none()

    def get_queryset(self):
        """
        Final QS: select_related + prefetch_related faqat shu yerda.
        """
        qs = self._base_queryset()

        # statement_ids - context uchun 1 marta
        if not hasattr(self, "_statement_ids"):
            self._statement_ids = list(qs.values_list("statement_id", flat=True).distinct())

        # report_items prefetch QILINMAYDI: item/qiymatlar list() da sahifadagi
        # hisobotlar uchun values() bilan yuklanadi (load_report_items) —
        # 200 hisobot x 120 ustun uchun ~100 000 model obyekti o'rniga lug'atlar.
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
            .prefetch_related("signatures")
            .order_by("-created_at")
        )
        return qs

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response([])
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        reports = page if page is not None else list(queryset)
        self._items_by_report = load_report_items([r.id for r in reports])
        serializer = self.get_serializer(reports, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

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
        context["items_by_report"] = getattr(self, "_items_by_report", None)

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
class ReportDeleteAPIView(DRFHistoryMixin, ReportScopedQuerysetMixin, CustomDestroyAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportDetailSerializer
    permission_classes = (CanDeleteReport,)
    lookup_field = 'id'


@extend_schema(tags=["Reports"])
class ReportRetrieveAPIView(ReportScopedQuerysetMixin, CustomRetrieveAPIView):
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
class ReportUpdateAPIView(DRFHistoryMixin, ReportScopedQuerysetMixin, CustomRetrieveUpdateAPIView):
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
    permission_classes = (CanEditReportData,)

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return ReportUpdateSerializer
        return ReportDetailSerializer