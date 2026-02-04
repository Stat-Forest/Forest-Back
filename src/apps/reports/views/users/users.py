from rest_framework import generics
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.users.models import CustomUser
from apps.reports.serializers.users import UserListSerializer
from apps.reports.filters import CustomUserFilter


@extend_schema(
    tags=["Users"],
    parameters=[
        OpenApiParameter(
            name="lang",
            description="Language parameter: uz (default) or ru",
            required=False,
            type=OpenApiTypes.STR,
            enum=["uz", "ru"],
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="first_name",
            description="Filter by first name (icontains search)",
            required=False,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="last_name",
            description="Filter by last name (icontains search)",
            required=False,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="organization",
            description="Filter by organization (UUID)",
            required=False,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="role",
            description="Filter by user role",
            required=False,
            type=OpenApiTypes.STR,
            enum=[choice[0] for choice in CustomUser.Role.choices],
            location=OpenApiParameter.QUERY,
        ),
    ],
)
class UserListAPIView(generics.ListAPIView):
    serializer_class = UserListSerializer
    queryset = CustomUser.objects.all()
    filterset_class = CustomUserFilter
    filter_backends = [filters.DjangoFilterBackend]

    def get_queryset(self):
        user = self.request.user

        qs = CustomUser.objects.select_related(
            "organization",
            "statement"
        )

        # SUPERUSER – hammasi
        if user.is_superuser:
            return qs

        # HUDUDIY BOSHQARMA (organization ham, statement ham yo‘q)
        if user.role == CustomUser.Role.HUDUDIY_BOSHQARMA:
            orgs = user.region_user_orgs.all()

            # himoya: noto‘g‘ri sozlama bo‘lsa
            if not orgs.exists():
                return qs.none()

            return qs.filter(
                organization__in=orgs
            )

        # ORGANIZATION USER
        if user.organization_id:
            return qs.filter(
                organization_id=user.organization_id
            )

        # STATEMENT USER
        if user.statement_id:
            return qs.filter(
                statement_id=user.statement_id
            )

        return qs.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz").lower()
        context["lang"] = lang
        return context
