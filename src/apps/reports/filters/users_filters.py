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

    id = filters.UUIDFilter(field_name="id")

    status_user = filters.ChoiceFilter(
        method="filter_status",
        choices=[
            ("online_user", "Online user"),
            ("login_user", "Login bo‘lgan user"),
            ("never_login_user", "Hech qachon login qilmagan"),
        ]
    )

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "first_name",
            "last_name",
            "organization",
            "role",
            "status_user",
        ]

    def filter_status(self, queryset, name, value):
        now = timezone.now()
        online_limit = now - timedelta(minutes=5)

        # 1️⃣ ONLINE → oxirgi 5 daqiqa ichida faollik bo‘lganlar
        if value == "online_user":
            return queryset.filter(
                last_activity__isnull=False,
                last_activity__gte=online_limit,
            )

        # 2️⃣ LOGIN_USER → login qilgan, lekin hozir online bo‘lmagan
        if value == "login_user":
            return queryset.filter(
                last_login__isnull=False,              # login qilgan
            ).filter(
                last_activity__lt=online_limit         # online emas
            )

        # 3️⃣ NEVER_LOGIN → last_login null
        if value == "never_login_user":
            return queryset.filter(
                last_login__isnull=True
            )

        return queryset
