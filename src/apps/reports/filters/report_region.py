import django_filters
from django.db.models import Q
from django.db.models.functions import ExtractYear

from apps.general.models import Republic
from apps.reports.models import Report
from apps.utils.services import PeriodChoices, RegionChoices


#organization_region -> ChoicesFilter, statement_period -> CharFilter, organization_name -> CharFilter, year -> NumberFilter, method=filter_by_year

class ReportFilter(django_filters.FilterSet):
    republic = django_filters.ModelChoiceFilter(
        queryset=Republic.objects.all(),
        method="filter_by_republic",
        label="Respublika"
    )
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

    organization_name = django_filters.CharFilter(
        field_name="organization__name",
        lookup_expr="icontains",
        label="tashkilot nomi"
    )

    year = django_filters.NumberFilter(
        method="filter_by_year",
        label="Yil"
    )

    general_report = django_filters.BooleanFilter(
        field_name="is_general",
        label="General Reports"
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

    def filter_by_organization_region(self, queryset, name, value):
        return queryset.filter(
            Q(organization__region=value) | Q(region=value, is_general=True)
        )

    def filter_by_republic(self, queryset, name, republic_obj):
        return queryset.filter(
            Q(organization__republic=republic_obj) | Q(republic=republic_obj))

    def filter_by_general_report(self, queryset):
        return queryset.filter(
            is_general=True
        )