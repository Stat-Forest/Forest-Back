from rest_framework import generics
from drf_spectacular.utils import extend_schema, OpenApiParameter
from apps.reports.filters import UserFilter, get_region_choices, get_organization_name_choices
from apps.reports.serializers import UserListSerializer
from apps.users.models import CustomUser

@extend_schema(tags=["Users"])
class UserListAPIView(generics.ListAPIView):
    queryset = CustomUser.objects.prefetch_related("personal_info__organizations")
    serializer_class = UserListSerializer
    filterset_class = UserFilter
    search_fields = ('first_name',)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                'region',
                type=str,
                description="Region filter",
                enum=[region for region, _ in get_region_choices()]
            ),
            OpenApiParameter(
                'organization_name',
                type=str,
                description="Organization Name filter",
                enum=[name for name, _ in get_organization_name_choices()]
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
