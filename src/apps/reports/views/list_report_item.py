from rest_framework.generics import ListAPIView
from drf_spectacular.utils import extend_schema

from apps.reports.models.report_item import ReportItem
from apps.reports.serializers.report_item import ReportItemSerializer
from apps.reports.models import Report
from apps.reports.permissions.report_scope import scope_reports_for_user


@extend_schema(tags=["Reports Items"])
class ReportItemListAPIView(ListAPIView):
    queryset = ReportItem.objects.select_related('report', 'statement_column')
    serializer_class = ReportItemSerializer
    pagination_class = None
    filterset_fields = ['report__id']

    def get_queryset(self):
        allowed_reports = scope_reports_for_user(Report.objects.all(), self.request.user)
        return super().get_queryset().filter(report__in=allowed_reports)
