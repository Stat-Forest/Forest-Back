from django_filters import rest_framework as filters

from apps.users.models import CustomUser
from apps.general.models import Organization
from apps.utils.services import RegionChoices


class CustomUserFilter(filters.FilterSet):
    organization__name = filters.ModelChoiceFilter(
        field_name="organization",
        queryset=Organization.objects.all(),
        to_field_name="name",
        label="Organization Name"
    )

    organization__region = filters.ChoiceFilter(
        field_name="organization__region",
        choices=RegionChoices.choices,
        label="Organization Region"
    )

    class Meta:
        model = CustomUser
        fields = ['first_name']