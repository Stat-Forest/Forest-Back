from rest_framework import generics
from drf_spectacular.utils import extend_schema, OpenApiParameter
# from apps.reports.filters import UserFilter, get_region_choices, get_organization_name_choices
from apps.reports.serializers import UserListSerializer
from apps.users.models import CustomUser

@extend_schema(tags=["Users"])
class UserListAPIView(generics.ListAPIView):
    queryset = CustomUser.objects.prefetch_related("organizations")
    serializer_class = UserListSerializer
