from apps.base.views import CustomListAPIView
from apps.reports.models import AllReport
from apps.reports.serializers import AllReportListSerializer


class AllReportListAPIView(CustomListAPIView):
    queryset = AllReport.objects.all()
    serializer_class = AllReportListSerializer