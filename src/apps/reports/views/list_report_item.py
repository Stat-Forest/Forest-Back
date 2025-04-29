from apps.reports.models import ReportItem
from apps.reports.serializers import ReportItemSerializer
from apps.base.views import CustomListAPIView

class ReportItemListAPIView(CustomListAPIView):
    queryset = ReportItem.objects.select_related('report', 'statement_column')
    serializer_class = ReportItemSerializer