import django_filters
from django.db.models.functions import ExtractYear

from apps.reports.models import Report
from apps.utils.services import PeriodChoices, RegionChoices


#organization_region -> ChoicesFilter, statement_period -> CharFilter, organization_name -> CharFilter, year -> NumberFilter, method=filter_by_year

class ReportFilter(django_filters.FilterSet):
    organization_region = django_filters.ChoiceFilter(
        field_name="organization__region",
        choices=RegionChoices.choices,
        label="Viloyat"
    )

    statement_period = django_filters.ChoiceFilter(
        field_name="statement__period",
        choices=PeriodChoices.choices,
        label="Hisobot Davri"
    )

    organization_name = django_filters.CharFilter(
        field_name="organization__name",
        lookup_expr="icontains",
        label="tashkilot nomi"
    )

    year = django_filters.NumberFilter(
        method="filter_by_year",
        label="Yil"
    )

    submit_period = django_filters.CharFilter(
        method="filter_by_submit_period",
        label="Davr (2025-04, 2025-Q1, 2025-W1, 2025)"
    )

    class Meta:
        model = Report
        fields = [
            "organization_region",
            "statement_period",
            "organization_name",
            "year"
        ]

    def filter_by_year(self, queryset, value):
        return queryset.annotate(
            submit_year=ExtractYear("deadline__submit_at")
        ).filter(submit_year=value)

    def filter_by_submit_period(self, queryset, name, value):
        return queryset.filter(deadline__submit_at__icontains=value)

    def filter_by_organization_region(self, queryset, name, value):
        return queryset.filter(organization__region=value)