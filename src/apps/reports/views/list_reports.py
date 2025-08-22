from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.base.views import CustomListAPIView, CustomRetrieveAPIView
from apps.reports.models import Report
from apps.reports.serializers import ReportListSerializer



class ExtraReportFilter(filters.FilterSet):
    class Meta:
        model = Report
        fields = {
            'statement': ['exact'],
            'deadline': ['exact'],
            'organization': ['exact'],
            'region': ['exact'],
        }


class IndividualGeneralReport(CustomListAPIView):
    queryset = Report.objects.filter(is_individual_general=True)
    serializer_class = ReportListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ExtraReportFilter


class IndividualGeneralReportDetail(CustomRetrieveAPIView):
    queryset = Report.objects.filter(is_individual_general=True)
    serializer_class = ReportListSerializer


class RegionalGeneralReport(CustomListAPIView):
    queryset = Report.objects.filter(is_general=True, is_republic=False)
    serializer_class = ReportListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ExtraReportFilter


class RegionalGeneralReportDetail(CustomRetrieveAPIView):
    queryset = Report.objects.filter(is_general=True, is_republic=False)
    serializer_class = ReportListSerializer


class RepublicGeneralReport(CustomListAPIView):
    queryset = Report.objects.filter(is_republic=True)
    serializer_class = ReportListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ExtraReportFilter


class RepublicGeneralReportDetail(CustomRetrieveAPIView):
    queryset = Report.objects.filter(is_republic=True)
    serializer_class = ReportListSerializer