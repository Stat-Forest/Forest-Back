from drf_spectacular.utils import extend_schema

from apps.reports.models import ReportItem
from apps.base.views import CustomListAPIView
from apps.reports.serializers import ReportItemSerializer


@extend_schema(tags=["Reports Items"])
class ReportItemListAPIView(CustomListAPIView):
    queryset = ReportItem.objects.select_related('report', 'statement_column')
    serializer_class = ReportItemSerializer
