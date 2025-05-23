from django.db.models import Q

from apps.base.views import CustomListAPIView
from apps.reports.models import StatementColumn
from apps.reports.serializers.plan_column import PlanColumnSerializer
from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Plan"])
class PlanStatementColumnListAPIView(CustomListAPIView):
    serializer_class = PlanColumnSerializer

    def get_queryset(self, *args, **kwargs):
        user = self.request.user
        base_filter = Q(parent__isnull=False)

        if user.statement:
            base_filter &= Q(statement__parent=user.statement)

        # Avval oy (monthly) planlarni olamiz:
        month_qs = StatementColumn.objects.filter(
            base_filter & Q(status_plan__in=[
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
            ])
        )
        if month_qs.exists():
            return month_qs.select_related(
                "parent",
                "parent__parent",
                "parent__parent__parent",
                "parent__parent__parent__parent",
                "parent__parent__parent__parent__parent"
            )

        # Oy planlari yo‘q bo‘lsa, chorak (quarter) planlarni olamiz:
        quarter_qs = StatementColumn.objects.filter(
            base_filter & Q(status_plan__in=[
                StatementColumn.PlanStatus.CHORAK_1,
                StatementColumn.PlanStatus.CHORAK_2,
                StatementColumn.PlanStatus.CHORAK_3,
                StatementColumn.PlanStatus.CHORAK_4,
            ])
        )
        if quarter_qs.exists():
            return quarter_qs.select_related(
                "parent",
                "parent__parent",
                "parent__parent__parent",
                "parent__parent__parent__parent",
                "parent__parent__parent__parent__parent"
            )

        year_qs = StatementColumn.objects.filter(
            base_filter & Q(status_plan=StatementColumn.PlanStatus.YILLIK)
        )
        return year_qs.select_related(
            "parent",
            "parent__parent",
            "parent__parent__parent",
            "parent__parent__parent__parent",
            "parent__parent__parent__parent__parent"
        )
