import django_filters

from django.db.models import Q
from django.db.models.functions import Substr

from apps.general.models import Republic
from apps.reports.models import Report, StatementColumn, Statement, Deadline
from apps.utils.services import PeriodChoices, RegionChoices
from apps.utils.translation import get_translated_field


class StatementColumnFilter(django_filters.FilterSet):
    statement = django_filters.ModelChoiceFilter(queryset=Statement.objects.filter(parent__isnull=False))

    class Meta:
        model = StatementColumn
        fields = ['statement']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        lang = "uz"
        if self.request:
            lang = self.request.GET.get("lang", "uz").lower()

        self.filters['statement'].label_from_instance = lambda obj: get_translated_field(obj, 'name', lang)


STATEMENT_QS = (
    Statement.objects
    .filter(parent__isnull=False)
    .only("id", "name_uz", "name_ru")
)

REPUBLIC_QS = (
    Republic.objects
    .only("id", "name")
)

# submit_at values cache (process-level)
_SUBMIT_AT_CHOICES_CACHE = None


def get_submit_at_choices():
    global _SUBMIT_AT_CHOICES_CACHE
    if _SUBMIT_AT_CHOICES_CACHE is None:
        values = (
            Deadline.objects
            .order_by("submit_at")
            .values_list("submit_at", flat=True)
            .distinct()
        )
        _SUBMIT_AT_CHOICES_CACHE = [("", "Hammasi")] + [(v, v) for v in values]
    return _SUBMIT_AT_CHOICES_CACHE


class ReportFilter(django_filters.FilterSet):
    organization_region = django_filters.ChoiceFilter(
        method="filter_by_organization_region",
        choices=RegionChoices.choices,
        label="Viloyat"
    )

    statement_period = django_filters.ChoiceFilter(
        field_name="statement__period",
        choices=PeriodChoices.choices,
        label="Hisobot Davri"
    )

    submit_at = django_filters.ChoiceFilter(
        method="filter_by_submit_at",
        label="Yuborish muddati",
        choices=[],
    )

    organization_name = django_filters.CharFilter(
        field_name="organization__name",
        lookup_expr="icontains",
        label="Tashkilot nomi"
    )

    year = django_filters.NumberFilter(
        method="filter_by_year",
        label="Yil"
    )

    status = django_filters.ChoiceFilter(
        field_name="status",
        choices=Report.StatusChoices.choices,
        label="Hisobot holati"
    )

    statement = django_filters.ModelChoiceFilter(
        field_name="statement",
        queryset=STATEMENT_QS,
        label="Hisobot turi"
    )
    time_status = django_filters.ChoiceFilter(
        field_name="time_status",
        choices=Report.TimeStatus.choices,
        label="Vaqt holati"
    )

    class Meta:
        model = Report
        fields = [
            "organization_region",
            "statement_period",
            "organization_name",
            "year",
            "statement",
            "submit_at",
            "time_status",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        lang = "uz"
        if self.request:
            lang = self.request.GET.get("lang", "uz").lower()

        # label_from_instance → DB yo‘q
        self.filters["statement"].label_from_instance = (
            lambda obj: get_translated_field(obj, "name", lang)
        )

        # submit_at choices — CACHED
        self.filters["submit_at"].extra["choices"] = get_submit_at_choices()

        # "Hammasi" default
        for f in self.filters.values():
            if isinstance(f, (django_filters.ChoiceFilter, django_filters.ModelChoiceFilter)):
                if not f.extra.get("choices") and hasattr(f, "field"):
                    try:
                        base = list(f.field.choices)
                        if ("", "Hammasi") not in base:
                            f.extra["choices"] = [("", "Hammasi")] + base
                    except Exception:
                        pass


    def filter_by_year(self, queryset, name, value):
        return queryset.filter(deadline__submit_at__year=value)

    def filter_by_organization_region(self, queryset, name, value):
        return queryset.filter(
            Q(organization__region=value) |
            Q(region=value, is_general=True)
        )

    def filter_by_submit_at(self, queryset, name, value):
        return queryset.filter(deadline__submit_at=value) if value else queryset