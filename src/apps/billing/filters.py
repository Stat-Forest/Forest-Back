"""
Shartnomalar filtri (list, summary, counts, geo-list, export uchun umumiy) va
ma'lumotnoma filtrlari.
"""
import django_filters
from django.db.models import F, Q

from apps.billing.models import Bolim, Contract

DATE_INPUT_FORMATS = ["%d.%m.%Y", "%Y-%m-%d"]
TRUE_VALUES = {"1", "true", "yes", "on"}

STATUS_CHOICES = Contract.Status.choices + [("all", "Barchasi")]


class BillingContractFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=STATUS_CHOICES, method="filter_status")
    xojalik = django_filters.UUIDFilter(field_name="xojalik_id")
    bolim = django_filters.UUIDFilter(field_name="bolim_id")
    region = django_filters.UUIDFilter(field_name="xojalik__region_id")
    district = django_filters.UUIDFilter(field_name="district_id")
    stir = django_filters.CharFilter(method="filter_stir")
    fullname = django_filters.CharFilter(field_name="renter__full_name", lookup_expr="icontains")
    number = django_filters.CharFilter(method="filter_number")
    from_date = django_filters.DateFilter(field_name="contract_date", lookup_expr="gte", input_formats=DATE_INPUT_FORMATS)
    to_date = django_filters.DateFilter(field_name="contract_date", lookup_expr="lte", input_formats=DATE_INPUT_FORMATS)
    debtors = django_filters.CharFilter(method="filter_debtors")
    search = django_filters.CharFilter(method="filter_search")
    ordering = django_filters.OrderingFilter(
        fields=(
            ("contract_date", "contract_date"),
            ("expired_date", "expired_date"),
            ("rent_amount", "rent_amount"),
            ("paid_amount", "paid_amount"),
            ("rent_area", "rent_area"),
            ("created_at", "created_at"),
            ("xojalik__name", "xojalik__name"),
        ),
    )

    class Meta:
        model = Contract
        fields = []

    def filter_status(self, queryset, name, value):
        if not value or value == "all":
            return queryset
        return queryset.filter(status=value)

    def filter_stir(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(Q(renter__pinfl__icontains=value) | Q(renter__stir__icontains=value))

    def filter_number(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(Q(number__icontains=value) | Q(contract_number__icontains=value))

    def filter_debtors(self, queryset, name, value):
        if str(value).strip().lower() in TRUE_VALUES:
            return queryset.filter(rent_amount__gt=F("paid_amount"))
        return queryset

    def filter_search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(number__icontains=value)
            | Q(contract_number__icontains=value)
            | Q(renter__full_name__icontains=value)
            | Q(renter__pinfl__icontains=value)
            | Q(renter__stir__icontains=value)
            | Q(xojalik__name__icontains=value)
        )


class BolimFilter(django_filters.FilterSet):
    xojalik = django_filters.UUIDFilter(field_name="xojalik_id")
    region = django_filters.UUIDFilter(field_name="xojalik__region_id")

    class Meta:
        model = Bolim
        fields = []
