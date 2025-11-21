from django_filters import rest_framework as filters
from django.utils import timezone
from datetime import timedelta

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

    # UUID filter
    id = filters.UUIDFilter(field_name="id")

    # 🔥 yangi filter
    status = filters.CharFilter(method="filter_status")

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "first_name",
            "last_name",
            "organization",
            "role",
            "status",   # <-- qo‘shildi
        ]

    def filter_status(self, queryset, name, value):
        value = value.lower()

        now = timezone.now()
        online_limit = now - timedelta(minutes=5)

        if value == "online_user":
            return queryset.filter(last_activity__gte=online_limit)

        if value == "login_user":
            return queryset.filter(
                last_login__isnull=False,
                last_activity__lt=online_limit
            )

        if value == "never_login_user":
            return queryset.filter(last_login__isnull=True)

        return queryset
