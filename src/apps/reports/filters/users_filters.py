# apps/reports/filters.py
from django_filters import rest_framework as filters
from apps.users.models.users import CustomUser
from apps.general.models import Organization


class CustomUserFilter(filters.FilterSet):
    # 🔍 first_name bo‘yicha alohida search
    first_name = filters.CharFilter(field_name="first_name", lookup_expr="icontains")
    # 🔍 last_name bo‘yicha alohida search
    last_name = filters.CharFilter(field_name="last_name", lookup_expr="icontains")

    # 🏢 organization obyektlari orqali filter
    organization = filters.ModelChoiceFilter(
        field_name="organization",
        queryset=Organization.objects.all()
    )

    # 👤 role bo‘yicha filter
    role = filters.ChoiceFilter(
        field_name="role",
        choices=CustomUser.Role.choices
    )

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "organization", "role"]
