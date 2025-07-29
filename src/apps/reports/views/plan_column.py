from django.db.models import Q
from apps.base.views import CustomListAPIView
from apps.reports.models import StatementColumn
from apps.reports.serializers.plan_column import PlanColumnSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter


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

        return queryset.filter(base_filter)

    def get_queryset(self):
        # Avval barcha obyektlarni olib kelamiz
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
