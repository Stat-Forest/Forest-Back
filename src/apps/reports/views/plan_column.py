from django.db.models import Q
from apps.base.views import CustomListAPIView
from apps.reports.models import StatementColumn
from apps.reports.serializers.plan_column import PlanColumnSerializer
from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Plan"])
class PlanStatementColumnListAPIView(CustomListAPIView):
    pagination_class = None
    serializer_class = PlanColumnSerializer

    def get_queryset(self):
        user = self.request.user
        base_filter = Q(parent__isnull=False) & Q(status_plan__isnull=False)

        if hasattr(user, 'statement') and user.statement:
            base_filter &= Q(statement__parent=user.statement)

        return StatementColumn.objects.filter(base_filter).select_related(
            "parent",
            "parent__parent",
            "parent__parent__parent",
            "parent__parent__parent__parent",
            "parent__parent__parent__parent__parent"
        )
