from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from apps.base.views import CustomListAPIView, CustomRetrieveAPIView
from apps.reports.models import Report
from apps.reports.serializers.reports import ReportListSerializer
from apps.reports.serializers.general_serializer import RegionalGeneralReportSerializer


class ExtraReportFilter(filters.FilterSet):
    class Meta:
        model = Report
        fields = {
            'statement': ['exact'],
            'deadline': ['exact'],
            'organization': ['exact'],
            'region': ['exact'],
        }


@extend_schema(tags=["Individual-Reports"])
class IndividualGeneralReport(CustomListAPIView):
    queryset = Report.objects.filter(is_individual_general=True)
    serializer_class = ReportListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ExtraReportFilter


@extend_schema(tags=["Individual-Reports"])
class IndividualGeneralReportDetail(CustomRetrieveAPIView):
    queryset = Report.objects.filter(is_individual_general=True)
    serializer_class = ReportListSerializer


@extend_schema(tags=["Regional-Reports"])
class RegionalGeneralReport(CustomListAPIView):
    queryset = Report.objects.filter(
        is_general=True,
        is_republic=False
    ).select_related("statement").prefetch_related(
        "report_items__inners",
        "report_items__statement_column"
    )
    serializer_class = RegionalGeneralReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ExtraReportFilter

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz")
        context["lang"] = lang
        return context


@extend_schema(tags=["Regional-Reports"])
class RegionalGeneralReportDetail(CustomRetrieveAPIView):
    queryset = Report.objects.filter(
        is_general=True,
        is_republic=False
    ).select_related("statement").prefetch_related(
        "report_items__inners",
        "report_items__statement_column"
    )
    serializer_class = RegionalGeneralReportSerializer


@extend_schema(tags=["Republic-Reports"])
class RepublicGeneralReport(CustomListAPIView):
    queryset = Report.objects.filter(is_republic=True)
    serializer_class = ReportListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ExtraReportFilter


@extend_schema(tags=["Republic-Reports"])
class RepublicGeneralReportDetail(CustomRetrieveAPIView):
    queryset = Report.objects.filter(is_republic=True)
    serializer_class = ReportListSerializer