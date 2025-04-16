
from apps.base.views import CustomListAPIView
from apps.reports.models import Report
from apps.reports.serializers import ReportListSerializer


class ReportListAPIView(CustomListAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportListSerializer
