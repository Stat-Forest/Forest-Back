from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import DestroyAPIView, RetrieveUpdateAPIView

from apps.reports.models import Report
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

class ReportListAPIView(CustomListAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportListSerializer
    permission_classes = (IsAuthenticated,)
    filterset_fields = ['status']



class ReportCreateAPIView(CustomCreateAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportCreateSerializer
    permission_classes = (CanCreateReport,)


class ReportDeleteAPIView(DestroyAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportDetailSerializer
    permission_classes = (CanUpdateReport,)
    lookup_field = 'id'

class ReportRetrieveUpdateAPIView(RetrieveUpdateAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportDetailSerializer
    permission_classes = (CanUpdateReport,)
    lookup_field = 'id'
