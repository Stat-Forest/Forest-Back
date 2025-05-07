from apps.base.views import CustomListAPIView
from apps.reports.models import StatementColumn
from apps.reports.serializers.plan_column import PlanColumnSerializer


class PlaneStatementColumnListAPIView(CustomListAPIView):
    serializer_class = PlanColumnSerializer

    def get_queryset(self, *args, **kwargs):
        columns = StatementColumn.objects.filter(parent__isnull=False, is_plane=True).select_related("parent",
                                                                                                     "parent__parent",
                                                                                                     "parent__parent__parent",
                                                                                                     "parent__parent__parent__parent")
        return columns
