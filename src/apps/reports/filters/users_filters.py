from django_filters import rest_framework as filters
from apps.users.models import CustomUser
from apps.general.models import Organization
from apps.utils.services import RegionChoices
class CustomUserFilter(filters.FilterSet):
    organizations__name = filters.ModelChoiceFilter(
        field_name="organizations",
        queryset=Organization.objects.all(),
        to_field_name="name",
        label="Organization Name"
    )

    organizations__region = filters.ChoiceFilter(
        field_name="organizations__region",
        choices=RegionChoices.choices,
        label="Organization Region"
    )

    class Meta:
        model = CustomUser
        fields = ['first_name']