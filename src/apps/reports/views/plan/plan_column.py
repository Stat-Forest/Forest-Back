# Django ORM imports
from django.db.models import Q, IntegerField
from django.db.models.functions import Cast
from django.db.models.expressions import Func, Value

# Project imports
from apps.base.views import CustomListAPIView
from apps.reports.models import StatementColumn
from apps.reports.serializers.plan import PlanColumnSerializer

# Swagger (drf-spectacular) imports
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

# Status constants
from apps.utils.services.variables import (
    MONTHLY_STATUSES,
    QUARTERLY_STATUSES,
    YEARLY_STATUSES,
    YEARLY_TOTAL_STATUSES,
)


# -----------------------------------------------------------------------------
# PostgreSQL SPLIT_PART wrapper
# -----------------------------------------------------------------------------
class SplitPart(Func):
    function = "SPLIT_PART"
    arity = 3


# -----------------------------------------------------------------------------
# Plan StatementColumn List API
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
class PlanStatementColumnListAPIView(CustomListAPIView):
    """
    API endpoint for listing StatementColumns related to Plan.

    Features:
    - Applies base filters (must have parent and status).
    - Restricts by user's statement if available.
    - Prioritizes statuses (monthly → quarterly → yearly → yearly total).
    - Orders results numerically by extracting last part of "ordering".
    """
    pagination_class = None
    serializer_class = PlanColumnSerializer
    filterset_fields = ["statement"]

    def filter_queryset(self, queryset):
        """
        Apply custom filtering and prioritize statuses.
        """
        queryset = super().filter_queryset(queryset)
        user = self.request.user

        # Base filter: only columns with parent and valid status
        base_filter = Q(parent__isnull=False) & Q(status_plan__isnull=False)

        # If user has statement, restrict by its parent
        if hasattr(user, "statement") and user.statement:
            base_filter &= Q(statement__parent=user.statement)

        queryset = queryset.filter(base_filter)

        # Get existing statuses in queryset
        existing_statuses = set(queryset.values_list("status_plan", flat=True))

        # Apply priority order
        if existing_statuses.intersection(MONTHLY_STATUSES):
            queryset = queryset.filter(status_plan__in=MONTHLY_STATUSES)
        elif existing_statuses.intersection(QUARTERLY_STATUSES):
            queryset = queryset.filter(status_plan__in=QUARTERLY_STATUSES)
        elif existing_statuses.intersection(YEARLY_STATUSES):
            queryset = queryset.filter(status_plan__in=YEARLY_STATUSES)
        elif existing_statuses.intersection(YEARLY_TOTAL_STATUSES):
            queryset = queryset.filter(status_plan__in=YEARLY_TOTAL_STATUSES)

        # Extract last number from "ordering" field for numeric sorting
        return queryset.annotate(
            last_num=Cast(
                SplitPart("ordering", Value("."), Value(-1)),
                IntegerField(),
            )
        ).order_by("last_num")

    def get_queryset(self):
        """
        Optimize queryset using select_related to fetch parent hierarchy.
        """
        return StatementColumn.objects.select_related(
            "parent",
            "parent__parent",
            "parent__parent__parent",
            "parent__parent__parent__parent",
            "parent__parent__parent__parent__parent",
        )

    def get_serializer_context(self):
        """
        Add 'lang' parameter into serializer context (default: uz).
        """
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz").lower()
        context["lang"] = lang
        return context
