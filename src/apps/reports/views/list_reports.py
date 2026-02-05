import django_filters
from drf_spectacular.utils import extend_schema

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response

from apps.base.views import CustomListAPIView, CustomRetrieveAPIView
from apps.reports.models import Report, Statement, Deadline, StatementColumn
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

    def get_queryset(self):
        """
        Optimize N+1 by selecting FKs and prefetching related items/inners once.
        Also cache statement_ids for StatementColumn preload in context.
        """
        qs = (
            Report.objects
            .filter(is_individual_general=True)
            .select_related(
                "organization",
                "organization__republic",
                "statement",
                "statement__parent",
                "deadline",
                "sent_by",
                "sent_by_org",
            )
        )
        # Replace dummy prefetch with actual Prefetch for report_items
        from django.db.models import Prefetch
        from apps.reports.models import ReportItem
        qs = qs.prefetch_related(
            Prefetch(
                "report_items",
                queryset=(
                    ReportItem.objects
                    .select_related("statement_column", "statement_column__parent")
                    .prefetch_related("inners")
                )
            )
        )

        # Cache statement_ids for context preload
        self._statement_ids = list(qs.values_list("statement_id", flat=True).distinct())
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz")
        context["lang"] = lang

        # Preload StatementColumns once for all statements in the page
        statement_ids = getattr(self, "_statement_ids", [])
        if statement_ids:
            columns = (
                StatementColumn.objects
                .filter(statement_id__in=statement_ids)
                .select_related("parent")
                .only("id", "parent_id", "ordering", "title_uz", "title_ru", "is_organization", "statement_id")
            )
            columns_by_statement_id = {}
            for col in columns:
                columns_by_statement_id.setdefault(str(col.statement_id), []).append(col)
            context["columns_by_statement_id"] = columns_by_statement_id
        else:
            context["columns_by_statement_id"] = {}

        return context


@extend_schema(tags=["Individual-Reports"])
class IndividualGeneralReportDetail(CustomRetrieveAPIView):
    queryset = (
        Report.objects
        .filter(is_individual_general=True)
        .select_related(
            "organization",
            "organization__republic",
            "statement",
            "statement__parent",
            "deadline",
            "sent_by",
            "sent_by_org",
        )
        .prefetch_related(
            "report_items__inners",
            "report_items__statement_column",
            "report_items__statement_column__parent",
        )
    )
    serializer_class = ReportListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz")
        context["lang"] = lang

        # Preload columns for this statement to avoid repeated queries in serializer
        report: Report = self.get_object()
        cols = (
            StatementColumn.objects
            .filter(statement_id=report.statement_id)
            .select_related("parent")
            .only("id", "parent_id", "ordering", "title_uz", "title_ru", "is_organization", "statement_id")
        )
        context["columns_by_statement_id"] = {str(report.statement_id): list(cols)}
        return context


@extend_schema(tags=["Regional-Reports"])
class RegionalGeneralReport(CustomListAPIView):
    serializer_class = RegionalGeneralReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ExtraReportFilter

    def get_queryset(self):
        qs = (
            Report.objects
            .filter(is_general=True, is_republic=False)
            .select_related("statement")
            .prefetch_related(
                "report_items",
                "report_items__inners",
            )
        )

        user = self.request.user

        # ✅ HUDUDIY_BOSHQARMA — region based filtering
        if user.is_authenticated and user.role == "hududiy_boshqarma":
            org_regions = (
                user.region_user_orgs
                .values_list("region", flat=True)
                .distinct()
            )

            if not org_regions:
                return qs.none()

            qs = qs.filter(region__in=org_regions)

        # 🔑 serializer uchun kerakli statement_id lar
        self.statement_ids = list(
            qs.values_list("statement_id", flat=True).distinct()
        )

        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()

        # lang
        context["lang"] = self.request.query_params.get("lang", "uz")

        # 🔥 ENG MUHIM JOY
        # StatementColumn ni 1 marta olib, dict qilamiz
        context["columns_by_id"] = {
            col.id: col
            for col in (
                StatementColumn.objects
                .filter(statement_id__in=getattr(self, "statement_ids", []))
                .select_related("parent")
            )
        }

        return context


@extend_schema(tags=["Regional-Reports"])
class RegionalGeneralReportDetail(CustomRetrieveAPIView):
    queryset = (
        Report.objects
        .filter(is_general=True, is_republic=False)
        .select_related("statement")
        .prefetch_related(
            "report_items",
            "report_items__inners",
        )
    )
    serializer_class = RegionalGeneralReportSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_authenticated and user.role == "hududiy_boshqarma":
            org_regions = (
                user.region_user_orgs
                .values_list("region", flat=True)
                .distinct()
            )

            if not org_regions:
                return qs.none()

            return qs.filter(region__in=org_regions)

        return qs

    def retrieve(self, request, *args, **kwargs):
        self._object = self.get_object()
        serializer = self.get_serializer(self._object)
        return Response(serializer.data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["lang"] = self.request.query_params.get("lang", "uz")
        report = self._object
        context["columns_by_id"] = {
            col.id: col
            for col in (
                StatementColumn.objects
                .filter(statement_id=report.statement_id)
                .select_related("parent")
            )
        }
        return context


@extend_schema(tags=["Republic-Reports"])
class RepublicGeneralReport(CustomListAPIView):
    serializer_class = RegionalGeneralReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ExtraReportFilter

    def get_queryset(self):
        user = self.request.user
        # HUDUDIY_BOSHQARMA: hide Republic General Reports completely
        if user.is_authenticated and getattr(user, 'role', None) == 'hududiy_boshqarma':
            return Report.objects.none()
        qs = (
            Report.objects
            .filter(is_republic=True)
            .select_related("statement")
            .prefetch_related(
                "report_items",
                "report_items__inners",
            )
        )
        self.statement_ids = list(
            qs.values_list("statement_id", flat=True).distinct()
        )
        return qs
    def get_serializer_context(self):
        context = super().get_serializer_context()
        # lang
        context["lang"] = self.request.query_params.get("lang", "uz")
        context["columns_by_id"] = {
            col.id: col
            for col in (
                StatementColumn.objects
                .filter(statement_id__in=getattr(self, "statement_ids", []))
                .select_related("parent")
            )
        }
        return context


@extend_schema(tags=["Republic-Reports"])
class RepublicGeneralReportDetail(CustomRetrieveAPIView):
    queryset = (
        Report.objects
        .filter(is_republic=True)
        .select_related("statement")
        .prefetch_related(
            "report_items",
            "report_items__inners",
        )
    )
    serializer_class = RegionalGeneralReportSerializer

    def get_queryset(self):
        """HUDUDIY_BOSHQARMA must not see Republic General Reports."""
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and getattr(user, 'role', None) == 'hududiy_boshqarma':
            return qs.none()
        return qs

    def retrieve(self, request, *args, **kwargs):
        self._object = self.get_object()
        serializer = self.get_serializer(self._object)
        return Response(serializer.data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["lang"] = self.request.query_params.get("lang", "uz")
        report = self._object
        context["columns_by_id"] = {
            col.id: col
            for col in (
                StatementColumn.objects
                .filter(statement_id=report.statement_id)
                .select_related("parent")
            )
        }
        return context
