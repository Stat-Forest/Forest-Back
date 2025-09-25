from rest_framework import generics
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.users.models import CustomUser
from apps.reports.serializers.users import UserListSerializer
from apps.reports.filters import CustomUserFilter

from django_filters import rest_framework as filters
from rest_framework import generics, filters as drf_filters

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
            name="search",
            description="Search by first_name or last_name",
            required=False,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
        ),
    ],
)
class UserListAPIView(generics.ListAPIView):
    serializer_class = UserListSerializer
    filterset_class = CustomUserFilter
    filter_backends = [drf_filters.SearchFilter, filters.DjangoFilterBackend]

    # first_name va last_name bo‘yicha search
    search_fields = ["first_name", "last_name"]

    def get_queryset(self):
        user = self.request.user
        qs = CustomUser.objects.select_related(
            "organization",
            "statement"
        )

        user_org = getattr(user, 'organization', None)

        if user_org:
            qs = qs.filter(organization=user_org)
        elif user.statement is not None:
            qs = qs.filter(statement_id=user.statement.pk)

        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz").lower()
        context["lang"] = lang
        return context
