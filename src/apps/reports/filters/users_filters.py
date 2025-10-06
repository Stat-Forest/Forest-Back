from django_filters import rest_framework as filters

from apps.users.models import CustomUser
from apps.general.models import Organization
from apps.utils.services import RegionChoices


class CustomUserFilter(filters.FilterSet):
    # Organization bo‘yicha filter (id orqali)
    organization = filters.ModelChoiceFilter(
        field_name="organization",
        queryset=Organization.objects.all(),
        label="Organization"
    )

    # Organization region bo‘yicha filter
    organization__region = filters.ChoiceFilter(
        field_name="organization__region",
        choices=RegionChoices.choices,
        label="Organization Region"
    )

    # Role bo‘yicha filter
    role = filters.ChoiceFilter(
        field_name="role",
        choices=CustomUser.Role.choices,
        label="User Role"
    )

    class Meta:
        model = CustomUser
        fields = ["organization", "organization__region", "role"]