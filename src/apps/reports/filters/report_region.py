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
            "statement",
            "submit_at"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        lang = "uz"
        if self.request:
            lang = self.request.GET.get("lang", "uz").lower()

        self.filters['statement'].label_from_instance = lambda obj: get_translated_field(obj, 'name', lang)

        if 'statement_column' in self.filters:
            self.filters['statement_column'].label_from_instance = lambda obj: get_translated_field(obj, 'title', lang)

        # Submit_at tanlovlari (bo'sh qiymat bilan)
        submit_at_values = (
            Deadline.objects
            .order_by("submit_at")
            .values_list("submit_at", flat=True)
            .distinct()
        )
        choices = [('', 'Hammasi')] + [(val, val) for val in submit_at_values]
        self.filters['submit_at'].extra['choices'] = choices

        for name, f in self.filters.items():
            if isinstance(f, (django_filters.ChoiceFilter, django_filters.ModelChoiceFilter)):
                if not f.extra.get('choices') and hasattr(f, 'field'):
                    try:
                        original_choices = list(f.field.choices)
                        if ('', 'Hammasi') not in original_choices:
                            f.extra['choices'] = [('', 'Hammasi')] + original_choices
                    except Exception:
                        pass


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

    def filter_by_submit_at(self, queryset, name, value):
        if value:
            return queryset.filter(deadline__submit_at=value)
        return queryset