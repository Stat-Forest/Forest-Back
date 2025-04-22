from apps.reports.models import Report
from apps.reports.serializers import (
    ReportListSerializer,
    ReportCreateSerializer,
    ReportDetailSerializer,
    ReportStatusUpdateSerializer
)
from apps.base.views import (
    CustomListAPIView,
    CustomCreateAPIView,
    CustomRetrieveAPIView,
    CustomUpdateAPIView
)

class ReportListAPIView(CustomListAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportListSerializer


class ReportCreateAPIView(CustomCreateAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportCreateSerializer


class ReportDetailAPIView(CustomRetrieveAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportDetailSerializer
    lookup_field = 'id'


class ReportStatusUpdateAPIView(CustomUpdateAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportStatusUpdateSerializer
    lookup_field = 'id'
