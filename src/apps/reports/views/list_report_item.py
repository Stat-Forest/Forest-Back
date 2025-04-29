from apps.reports.models import ReportItem
from apps.base.views import CustomListAPIView
from apps.reports.serializers import ReportItemSerializer

class ReportItemListAPIView(CustomListAPIView):
    queryset = ReportItem.objects.select_related('report', 'statement_column')
    serializer_class = ReportItemSerializer