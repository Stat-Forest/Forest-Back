from drf_spectacular.utils import extend_schema
from rest_framework.generics import DestroyAPIView, RetrieveUpdateAPIView

from apps.reports.models import Report
# from apps.reports.permissions import CanCreateReport, CanUpdateReport
from apps.reports.serializers import (
    ReportListSerializer,
    ReportCreateSerializer,
    ReportDetailSerializer,
)
from apps.base.views import (
    CustomListAPIView,
    CustomCreateAPIView,
)


@extend_schema(tags=["Reports"])
class ReportListAPIView(CustomListAPIView):
    queryset = Report.objects.select_related(
        'organization',
        'statement',
        'deadline',
    ).filter(statement__parent__isnull=False).order_by('-created_at')
    serializer_class = ReportListSerializer
    filterset_fields = ['status','organization','statement','statement__period' ]


@extend_schema(tags=["Reports"])
class ReportCreateAPIView(CustomCreateAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportCreateSerializer
    # permission_classes = (CanCreateReport,)


@extend_schema(tags=["Reports"])
class ReportDeleteAPIView(DestroyAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportDetailSerializer
    # permission_classes = (CanUpdateReport,)
    lookup_field = 'id'


@extend_schema(tags=["Reports"])
class ReportRetrieveUpdateAPIView(RetrieveUpdateAPIView):
    queryset = Report.objects.select_related(
        'statement',
        'deadline__statement',
        'deadline',
    ).prefetch_related('items').distinct().order_by('-created_at')
    serializer_class = ReportDetailSerializer
    # permission_classes = (CanUpdateReport,)
    lookup_field = 'id'
