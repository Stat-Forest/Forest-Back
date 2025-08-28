# Standard library
from django.db import transaction
from django.utils.translation import gettext_lazy as _

# Third-party
from rest_framework import generics, status
from rest_framework.response import Response
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

# Local apps
from apps.reports.models import Plan, PlanItem
from apps.reports.serializers.plan import PlanSerializer, PlanListSerializer
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.permissions import CanCreatePlan
from apps.utils.translation import get_lang_code, get_translated_field


# -----------------------------------------------------------------------------
# Plan Create API
# -----------------------------------------------------------------------------
@extend_schema(tags=["Plan"])
class PlanCreateView(generics.CreateAPIView):
    """
    Create a new Plan.
    """
    queryset = Plan.objects.select_related("organization", "statement")
    serializer_class = PlanSerializer
    permission_classes = [CanCreatePlan]


# -----------------------------------------------------------------------------
# Plan Retrieve API
# -----------------------------------------------------------------------------
@extend_schema(tags=["Plan"])
class PlanRetrieveAPIView(generics.RetrieveAPIView):
    """
    Retrieve a single Plan by ID.
    """
    queryset = Plan.objects.select_related("organization", "statement")
    serializer_class = PlanSerializer
    # permission_classes = [CanCreatePlan]


# -----------------------------------------------------------------------------
# Plan List API
# -----------------------------------------------------------------------------
@extend_schema(
    tags=["Plan"],
    parameters=[
        OpenApiParameter(
            name="lang",
            description="Language parameter: uz (default) or ru",
            required=False,
            type=OpenApiTypes.STR,
            enum=["uz", "ru"],
            location=OpenApiParameter.QUERY,
        )
    ],
)
class PlanListAPIView(generics.ListAPIView):
    """
    List Plans filtered by user's organization and user's statement_parent_id.
    Language parameter (lang) is passed to serializer context.
    """
    queryset = (
        Plan.objects.select_related("organization", "statement")
        .prefetch_related("plan_items__column")
    )
    serializer_class = PlanListSerializer
    filterset_fields = ["statement", "organization", "year"]

    def get_queryset(self):
        """
        Restrict queryset to user's organization and user's statement parent.
        """
        user = self.request.user
        qs = self.queryset

        # Organization bo‘yicha filter
        if user.organization is not None:
            qs = qs.filter(organization_id=user.organization.pk)

        # User.statement_parent_id bo‘yicha filter
        if hasattr(user, 'statement') and user.statement is not None:
            qs = qs.filter(statement__parent_id=user.statement.id)

        return qs

    def get_serializer_context(self):
        """
        Add 'lang' parameter to serializer context (default: uz).
        """
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz")
        context["lang"] = lang
        return context


# -----------------------------------------------------------------------------
# Plan Delete API
# -----------------------------------------------------------------------------
@extend_schema(tags=["Plan"])
class PlanDeleteAPIView(generics.DestroyAPIView):
    """
    Delete a Plan by ID.
    Raises a custom exception if deletion fails.
    """
    queryset = Plan.objects.all()

    def delete(self, request, *args, **kwargs):
        try:
            return self.destroy(request, *args, **kwargs)
        except Exception as e:
            raise CustomExceptionError(detail={"error": str(e)})
