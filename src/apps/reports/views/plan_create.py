from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from rest_framework import generics
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from apps.reports.models import Plan, StatementColumn
from apps.reports.serializers import PlanSerializer, PlanListSerializer
from apps.base.exceptions.exception_files import CustomExceptionError


@extend_schema(tags=["Plan"])
class PlanCreateView(generics.CreateAPIView):
    queryset = Plan.objects.select_related('organization', 'column','statement')
    serializer_class = PlanSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            plan = serializer.save()
            organization = plan.organization
            year = plan.year
            statement = plan.statement
            column = plan.column

            if column.statement_id != statement.id:
                raise CustomExceptionError(400, _('Statement does not match column statement'))

            self.create_quarterly_plans(organization, year, statement)
            self.create_yearly_plan(organization, year, statement)
            self.create_total_yearly_plan(organization, year, statement)

    def create_quarterly_plans(self, organization, year, statement):
        chorak_map = {
            StatementColumn.PlanStatus.CHORAK_1: [
                StatementColumn.PlanStatus.YANVAR,
                StatementColumn.PlanStatus.FEVRAL,
                StatementColumn.PlanStatus.MART,
            ],
            StatementColumn.PlanStatus.CHORAK_2: [
                StatementColumn.PlanStatus.APREL,
                StatementColumn.PlanStatus.MAY,
                StatementColumn.PlanStatus.IYUN,
            ],
            StatementColumn.PlanStatus.CHORAK_3: [
                StatementColumn.PlanStatus.IYUL,
                StatementColumn.PlanStatus.AVGUST,
                StatementColumn.PlanStatus.SENTABR,
            ],
            StatementColumn.PlanStatus.CHORAK_4: [
                StatementColumn.PlanStatus.OKTABR,
                StatementColumn.PlanStatus.NOYABR,
                StatementColumn.PlanStatus.DEKABR,
            ],
        }

        for quarter_status, month_statuses in chorak_map.items():
            month_columns = StatementColumn.objects.filter(
                status_plan__in=month_statuses, statement=statement
            )

            if month_columns.count() != 3:
                continue

            month_plans = Plan.objects.filter(
                organization=organization,
                statement=statement,
                year=year,
                column__in=month_columns
            )

            if month_plans.count() != 3:
                continue

            total_value = sum(p.plan_value for p in month_plans)

            quarter_column = StatementColumn.objects.filter(
                status_plan=quarter_status, statement=statement
            ).first()

            if quarter_column:
                Plan.objects.update_or_create(
                    organization=organization,
                    statement=statement,
                    column=quarter_column,
                    year=year,
                    defaults={'plan_value': total_value}
                )

    def create_yearly_plan(self, organization, year, statement):
        quarterly_columns = StatementColumn.objects.filter(
            status_plan__in=[
                StatementColumn.PlanStatus.CHORAK_1,
                StatementColumn.PlanStatus.CHORAK_2,
                StatementColumn.PlanStatus.CHORAK_3,
                StatementColumn.PlanStatus.CHORAK_4
            ],
            statement=statement
        )

        if quarterly_columns.count() != 4:
            return

        quarter_plans = Plan.objects.filter(
            organization=organization,
            statement=statement,
            year=year,
            column__in=quarterly_columns
        )

        if quarter_plans.count() != 4:
            return

        total_value = sum(p.plan_value for p in quarter_plans)

        year_columns = StatementColumn.objects.filter(
            status_plan=StatementColumn.PlanStatus.YILLIK,
            statement=statement
        )

        for year_column in year_columns:
            Plan.objects.update_or_create(
                organization=organization,
                statement=statement,
                column=year_column,
                year=year,
                defaults={'plan_value': total_value}
            )

    def create_total_yearly_plan(self, organization, year, statement):
        yil_cols = StatementColumn.objects.filter(
            status_plan=StatementColumn.PlanStatus.YILLIK,
            statement=statement
        )

        plan_qs = Plan.objects.filter(
            organization=organization,
            statement=statement,
            year=year,
            column__in=yil_cols
        )

        if not plan_qs.exists():
            return

        total_value = sum(p.plan_value for p in plan_qs)

        total_col = StatementColumn.objects.filter(
            statement=statement,
            status_plan=StatementColumn.PlanStatus.YILLIK_TOTAL
        ).first()

        if total_col:
            Plan.objects.update_or_create(
                organization=organization,
                statement=statement,
                column=total_col,
                year=year,
                defaults={'plan_value': total_value}
            )


@extend_schema(tags=["Plan"])
class PlanListAPIView(generics.ListAPIView):
    queryset = Plan.objects.select_related('organization', 'column', 'statement')
    serializer_class = PlanListSerializer
    filterset_fields = ['column__id', 'statement', 'organization', 'year']

    def get_queryset(self):
        queryset = self.queryset
        user = self.request.user
        if user.statement is not None:
            return queryset.filter(statement__parent=user.statement)
        return queryset