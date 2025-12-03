from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.response import Response

from apps.reports.filters.report_region import ReportFilter
from apps.reports.models import Report, Plant, ReportItem
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
    CustomCreateAPIView, CustomRetrieveAPIView, CustomUpdateAPIView, CustomDestroyAPIView, CustomRetrieveUpdateAPIView,
)
from apps.logs.drf_mixins import DRFHistoryMixin


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
    # permission_classes = (CanListReport,)

    queryset = Report.objects.select_related(
        'organization',
        'statement',
        'statement__parent',
        'deadline',
        'sent_by',
        'sent_by_org'
    ).prefetch_related(
        Prefetch(
            'report_items',
            queryset=ReportItem.objects
            .select_related('statement_column', 'statement_column__parent')
            .prefetch_related("inners")
        )
    ).filter(
        statement__parent__isnull=False,
    ).order_by('-created_at')
    serializer_class = ReportListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReportFilter

    # filterset_fields = [
    #     'status', 'organization__name', 'organization',
    #     'statement__name', 'statement', 'statement__period',
    #     'organization__region', 'deadline__submit_at'
    # ]

    def get_queryset(self):
        user = self.request.user
        base_qs = self.queryset

        if not user.is_authenticated:
            return Report.objects.none()

        if user.is_superuser:
            return base_qs.filter(
                is_general=False,
                is_individual_general=False,
                is_republic=False,
            ).order_by('-created_at')

        if user.role in ['tashkilot_hodimi', 'hududiy_boshqarma', 'tashkilot_rahbari']:
            return base_qs.filter(
                organization=user.organization,
                is_general=False,
                is_individual_general=False,
                is_republic=False,
            ).order_by('-created_at')

        elif user.role == 'bolim_admin':
            return base_qs.filter(
                statement__parent_id=user.statement.id,
                is_general=False,
                is_individual_general=False,
                is_republic=False,
            ).order_by('-created_at')

        return base_qs.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz")
        context["lang"] = lang
        plant_qs = Plant.objects.only("id", "name")
        context["plant_map"] = {str(p.id): p.name for p in plant_qs}
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