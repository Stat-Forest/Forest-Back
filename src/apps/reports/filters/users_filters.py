# apps/reports/filters.py
from django_filters import rest_framework as filters
from apps.users.models.users import CustomUser
from apps.general.models import Organization


class CustomUserFilter(filters.FilterSet):
    first_name = filters.CharFilter(field_name="first_name", lookup_expr="icontains")
    last_name = filters.CharFilter(field_name="last_name", lookup_expr="icontains")

    organization = filters.ModelChoiceFilter(
        field_name="organization",
        queryset=Organization.objects.all()
    )

    role = filters.ChoiceFilter(
        field_name="role",
        choices=CustomUser.Role.choices
    )

    # 🆔 id bo‘yicha UUID filter
    id = filters.UUIDFilter(field_name="id")

    class Meta:
        model = CustomUser
        fields = ["id", "first_name", "last_name", "organization", "role"]
