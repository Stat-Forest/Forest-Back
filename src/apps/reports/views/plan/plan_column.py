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
from django.db.models import Value, CharField
from django.db.models.functions import Concat


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
    """
    pagination_class = None
    serializer_class = PlanColumnSerializer
    filterset_fields = ["statement"]

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        user = self.request.user

        base_filter = Q(parent__isnull=False) & Q(status_plan__isnull=False)

        if hasattr(user, "statement") and user.statement:
            base_filter &= Q(statement__parent=user.statement)

        queryset = queryset.filter(base_filter)

        # Extract existing statuses
        existing_statuses = set(queryset.values_list("status_plan", flat=True))

        # ---------------------------------------------------------
        # YILLIK_1, YILLIK_2 → YILLIK_3 ni CHIQARMASLIK (faqat 3 tasi uchun)
        # LEKIN oddiy YILLIK (status_plan="yillik") chiqishi shart!
        # ---------------------------------------------------------
        Y1 = "yillik_1"
        Y2 = "yillik_2"
        Y3 = "yillik_3"

        # Agar yig'indiyilliklar bor bo'lsa → faqat y1, y2 chiqsin, y3 chiqmasin
        if Y1 in existing_statuses or Y2 in existing_statuses:
            filtered_yearly_statuses = {Y1, Y2, "yillik"}  # oddiy YILLIK qoldiriladi!
        else:
            filtered_yearly_statuses = YEARLY_STATUSES
        # ---------------------------------------------------------

        # PRIORITY HANDLING
        if existing_statuses.intersection(MONTHLY_STATUSES):
            queryset = queryset.filter(status_plan__in=MONTHLY_STATUSES)

        elif existing_statuses.intersection(QUARTERLY_STATUSES):
            queryset = queryset.filter(status_plan__in=QUARTERLY_STATUSES)

        elif existing_statuses.intersection(YEARLY_STATUSES):
            queryset = queryset.filter(status_plan__in=filtered_yearly_statuses)

        elif existing_statuses.intersection(YEARLY_TOTAL_STATUSES):
            queryset = queryset.filter(status_plan__in=YEARLY_TOTAL_STATUSES)

        # Build parent full title
        queryset = queryset.annotate(
            parent_full_title=Concat(
                'parent__parent__parent__parent__parent__title_uz', Value(' - '),
                'parent__parent__parent__parent__title_uz', Value(' - '),
                'parent__parent__parent__title_uz', Value(' - '),
                'parent__parent__title_uz', Value(' - '),
                'parent__title_uz',
                output_field=CharField()
            )
        )

        return queryset.annotate(
            last_num=Cast(
                SplitPart("ordering", Value("."), Value(-1)),
                IntegerField(),
            )
        ).order_by("parent_full_title", "last_num")

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
