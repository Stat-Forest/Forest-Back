import django_filters
from drf_spectacular.utils import extend_schema

from django_filters.rest_framework import DjangoFilterBackend

from apps.base.views import CustomListAPIView, CustomRetrieveAPIView
from apps.reports.models import Report, Statement, Deadline
from apps.reports.serializers.reports import ReportListSerializer
from apps.reports.serializers.general_serializer import RegionalGeneralReportSerializer
from apps.utils.services import PeriodChoices, RegionChoices


class ExtraReportFilter(django_filters.FilterSet):
    statement_period = django_filters.ChoiceFilter(
        method='filter_statement_period',
        label="Hisobot davri",
        choices=[('', 'All')] + list(PeriodChoices.choices),
    )
    organization = django_filters.CharFilter(
        method='filter_organization',
        label="Tashkilot",
    )
    region = django_filters.ChoiceFilter(
        method='filter_region',
        choices=[('', 'All')] + list(RegionChoices.choices),
        label="Hudud"
    )
    statement = django_filters.ChoiceFilter(
        method='filter_statement',
        label="Hisobot turi",
        choices=lambda: [('', 'All')] + list(
            Statement.objects.filter(
                reports__isnull=False
            ).distinct().order_by('name_uz')
            .values_list('id', 'name_uz')
        )
    )

    deadline = django_filters.ChoiceFilter(
        method='filter_deadline',
        label="Muddat",
        choices=lambda: [('', 'All')] + list(
            Deadline.objects.filter(
                reports__isnull=False
            ).distinct().order_by('-submit_at')
            .values_list('id', 'submit_at')
        )
    )

    time_status = django_filters.ChoiceFilter(
        method='filter_time_status',
        label="Vaqt holati",
        choices=[('', 'All')] + list(Report.TimeStatus.choices)
    )

    def filter_statement_period(self, queryset, name, value):
        if value:
            return queryset.filter(statement__period=value)
        return queryset

    def filter_organization(self, queryset, name, value):
        if value:
            return queryset.filter(organization=value)
        return queryset

    def filter_region(self, queryset, name, value):
        if value:
            return queryset.filter(region=value)
        return queryset

    def filter_statement(self, queryset, name, value):
        if value:
            return queryset.filter(statement_id=value)
        return queryset

    def filter_deadline(self, queryset, name, value):
        if value:
            return queryset.filter(deadline_id=value)
        return queryset

    def filter_time_status(self, queryset, name, value):
        if value:
            return queryset.filter(time_status=value)
        return queryset


@extend_schema(tags=["Individual-Reports"])
class IndividualGeneralReport(CustomListAPIView):
    queryset = Report.objects.filter(is_individual_general=True)
    serializer_class = ReportListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ExtraReportFilter

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz")
        context["lang"] = lang
        return context


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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz")
        context["lang"] = lang
        return context


@extend_schema(tags=["Republic-Reports"])
class RepublicGeneralReportDetail(CustomRetrieveAPIView):
    queryset = Report.objects.filter(is_republic=True)
    serializer_class = ReportListSerializer