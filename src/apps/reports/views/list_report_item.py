from rest_framework.generics import ListAPIView
from drf_spectacular.utils import extend_schema

from apps.reports.models.report_item import ReportItem
from apps.reports.serializers import ReportItemSerializer


@extend_schema(tags=["Reports Items"])
class ReportItemListAPIView(ListAPIView):
    queryset = ReportItem.objects.select_related('report', 'statement_column')
    serializer_class = ReportItemSerializer
    filterset_fields = ['id']
