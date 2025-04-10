from src.apps.base.views import CustomListAPIView
from src.apps.reports.models import Report
from src.apps.reports.serializers import  ReportListSerializer


class ReportListAPIView(CustomListAPIView):
        queryset = Report.objects.all()
        serializer_class =  ReportListSerializer
