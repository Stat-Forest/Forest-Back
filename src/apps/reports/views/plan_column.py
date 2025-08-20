from django.db.models import Q
from apps.base.views import CustomListAPIView
from apps.reports.models import StatementColumn
from apps.reports.serializers.plan_column import PlanColumnSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter


MONTHLY_STATUSES = [
    StatementColumn.PlanStatus.YANVAR,
    StatementColumn.PlanStatus.FEVRAL,
    StatementColumn.PlanStatus.MART,
    StatementColumn.PlanStatus.APREL,
    StatementColumn.PlanStatus.MAY,
    StatementColumn.PlanStatus.IYUN,
    StatementColumn.PlanStatus.IYUL,
    StatementColumn.PlanStatus.AVGUST,
    StatementColumn.PlanStatus.SENTABR,
    StatementColumn.PlanStatus.OKTABR,
    StatementColumn.PlanStatus.NOYABR,
    StatementColumn.PlanStatus.DEKABR,
]

QUARTERLY_STATUSES = [
    StatementColumn.PlanStatus.CHORAK_1,
    StatementColumn.PlanStatus.CHORAK_2,
    StatementColumn.PlanStatus.CHORAK_3,
    StatementColumn.PlanStatus.CHORAK_4,
]

YEARLY_STATUSES = [
    StatementColumn.PlanStatus.YILLIK,
    StatementColumn.PlanStatus.YILLIK_TOTAL,
]


@extend_schema(
    tags=["Plan"],
    parameters=[
        OpenApiParameter(name="lang", description="Language: uz, ru", required=False, type=str),
    ]
)
class PlanStatementColumnListAPIView(CustomListAPIView):
    pagination_class = None
    serializer_class = PlanColumnSerializer
    filterset_fields = ['statement']

    def filter_queryset(self, queryset):
        """
        DRF filtering + custom filtering
        """
        queryset = super().filter_queryset(queryset)

        user = self.request.user
        base_filter = Q(parent__isnull=False) & Q(status_plan__isnull=False)

        if hasattr(user, 'statement') and user.statement:
            base_filter &= Q(statement__parent=user.statement)

        queryset = queryset.filter(base_filter)

        # Barcha mavjud statuslarni olish (distinct)
        existing_statuses = set(queryset.values_list("status_plan", flat=True))

        # Ustuvorlik bo'yicha filtr tanlash
        if existing_statuses.intersection(MONTHLY_STATUSES):
            queryset = queryset.filter(status_plan__in=MONTHLY_STATUSES)
        elif existing_statuses.intersection(QUARTERLY_STATUSES):
            queryset = queryset.filter(status_plan__in=QUARTERLY_STATUSES)
        elif existing_statuses.intersection(YEARLY_STATUSES):
            queryset = queryset.filter(status_plan__in=YEARLY_STATUSES)

        return queryset

    def get_queryset(self):
        return StatementColumn.objects.select_related(
            "parent",
            "parent__parent",
            "parent__parent__parent",
            "parent__parent__parent__parent",
            "parent__parent__parent__parent__parent"
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz").lower()
        context["lang"] = lang
        return context
