from rest_framework import generics

from drf_spectacular.utils import extend_schema
from django_filters import rest_framework as filters

from apps.users.models import CustomUser
from apps.general.models import Organization
from apps.reports.serializers import UserListSerializer
from apps.reports.filters import CustomUserFilter



@extend_schema(tags=["Users"])
class UserListAPIView(generics.ListAPIView):
    serializer_class = UserListSerializer
    filterset_class = CustomUserFilter

    def get_queryset(self):
        user = self.request.user

        qs = CustomUser.objects.prefetch_related(
            "organization",
            "statement"
        )

        user_org = getattr(user, 'organization', None)
        user_stmt = getattr(user, 'statement', None)

        if user_org and user_stmt:
            qs = qs.filter(
                organizations=user_org,
                statement__parent=user_stmt
            )

        return qs





