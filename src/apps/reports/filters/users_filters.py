from django_filters import rest_framework as filters
from apps.users.models import CustomUser
from apps.general.models import Organization
from functools import lru_cache


@lru_cache()
def get_region_choices():
    regions = Organization.objects.values_list("region", flat=True).distinct()
    return [(region, region) for region in regions if region]


@lru_cache()
def get_organization_name_choices():
    names = Organization.objects.values_list("name", flat=True).distinct()
    return [(name, name) for name in names if name]


class UserFilter(filters.FilterSet):
    region = filters.ChoiceFilter(
        field_name='personal_info__organizations__region',
        choices=get_region_choices,
        label="Region"
    )

    organization_name = filters.ChoiceFilter(
        field_name='personal_info__organizations__name',
        choices=get_organization_name_choices,
        label="Organization Name"
    )

    class Meta:
        model = CustomUser
        fields = ['region', 'organization_name']

