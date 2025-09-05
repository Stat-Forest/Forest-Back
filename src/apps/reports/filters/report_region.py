import django_filters
from django.db.models import Q
from django.db.models.functions import Substr

from apps.general.models import Republic
from apps.reports.models import Report, StatementColumn, Statement
from apps.utils.services import PeriodChoices, RegionChoices
from apps.utils.translation import get_translated_field


#organization_region -> ChoicesFilter, statement_period -> CharFilter, organization_name -> CharFilter, year -> NumberFilter, method=filter_by_year


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

    status = django_filters.ChoiceFilter(
        field_name="status",
        choices=Report.StatusChoices.choices,
        label="Type of reports"
    )

    statement = django_filters.ModelChoiceFilter(
        field_name="statement",
        queryset=Statement.objects.filter(parent__isnull=False),
        label="Hisobot turi"
    )

    class Meta:
        model = Report
        fields = [
            "organization_region",
            "statement_period",
            "organization_name",
            "year",
            "statement"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        lang = "uz"
        if self.request:
            lang = self.request.GET.get("lang", "uz").lower()

        self.filters['statement'].label_from_instance = lambda obj: get_translated_field(obj, 'name', lang)

        if 'statement_column' in self.filters:
            self.filters['statement_column'].label_from_instance = lambda obj: get_translated_field(obj, 'title', lang)

    def filter_by_year(self, queryset, name, value):
        return queryset.annotate(
            submit_year=Substr("deadline__submit_at", 1, 4)
        ).filter(submit_year=value)

    def filter_by_organization_region(self, queryset, name, value):
        return queryset.filter(
            Q(organization__region=value) | Q(region=value, is_general=True)
        )

    def filter_by_republic(self, queryset, name, republic_obj):
        return queryset.filter(
            Q(organization__republic=republic_obj) | Q(republic=republic_obj))