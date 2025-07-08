from drf_spectacular.utils import extend_schema
from rest_framework.generics import DestroyAPIView, RetrieveUpdateAPIView

from apps.reports.models import Report, Plant
from apps.reports.permissions import CanCreateReport, CanUpdateReport
from apps.reports.serializers import (
    ReportListSerializer,
    ReportCreateSerializer,
    ReportDetailSerializer,
)
from apps.base.views import (
    CustomListAPIView,
    CustomCreateAPIView,
)


@extend_schema(tags=["Reports"])
class ReportListAPIView(CustomListAPIView):
    pagination_class = None
    queryset = Report.objects.select_related(
        'organization',
        'statement',
        'deadline',
    ).prefetch_related(
        'report_items',
        'report_items__statement_column',
    ).filter(
        statement__parent__isnull=False
    ).order_by('-created_at')

    serializer_class = ReportListSerializer
    filterset_fields = [
        'status', 'organization__name','organization', 'statement__name','statement', 'statement__period', 'organization__region']

    def get_queryset(self):
        user = self.request.user
        if user.organization is not None:
            return self.queryset.filter(organization_id=user.organization.pk)

        elif user.statement is not None:
            return self.queryset.filter(statement__parent_id=user.statement.pk)

        return self.queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz")
        context["lang"] = lang
        plant_qs = Plant.objects.only("id", "name")
        context["plant_map"] = {str(p.id): p.name for p in plant_qs}
        return context


@extend_schema(tags=["Reports"])
class ReportCreateAPIView(CustomCreateAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportCreateSerializer
    permission_classes = (CanCreateReport,)


@extend_schema(tags=["Reports"])
class ReportDeleteAPIView(DestroyAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportDetailSerializer
    permission_classes = (CanUpdateReport,)
    lookup_field = 'id'


@extend_schema(tags=["Reports"])
class ReportRetrieveUpdateAPIView(RetrieveUpdateAPIView):
    queryset = Report.objects.select_related(
        'statement',
        'deadline__statement',
        'deadline',
    ).prefetch_related('report_items').distinct().order_by('-created_at')
    serializer_class = ReportDetailSerializer
    permission_classes = (CanUpdateReport,)
    lookup_field = 'id'
