from django.db import transaction
from django.db.models import Sum, Q
from rest_framework import generics, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from apps.reports.models import Plan, StatementColumn
from apps.reports.serializers import PlanSerializer


@extend_schema(tags=["Plan"])
class PlanCreateView(generics.CreateAPIView):
    queryset = Plan.objects.select_related('organization', 'column')
    serializer_class = PlanSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            plan = serializer.save()
            organization = plan.organization
            year = plan.year
            statement = plan.column.statement

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

            for chorak_status, oy_status_list in chorak_map.items():
                oy_columns = list(
                    StatementColumn.objects.filter(
                        status_plan__in=oy_status_list,
                        statement=statement
                    )
                )

                if len(oy_columns) != 3:
                    continue

                oy_plans = list(
                    Plan.objects.filter(
                        organization=organization,
                        column__in=oy_columns,
                        year=year
                    )
                )

                if len(oy_plans) != 3:
                    continue
                total_value = sum(p.plan_value for p in oy_plans)
                chorak_column = StatementColumn.objects.filter(
                    status_plan=chorak_status,
                    statement=statement
                ).first()

                if chorak_column:
                    Plan.objects.update_or_create(
                        organization=organization,
                        statement=statement,
                        column=chorak_column,
                        year=year,
                        defaults={'plan_value': total_value}
                    )

            all_chorak_columns = StatementColumn.objects.filter(
                status_plan__in=chorak_map.keys(),
                statement=statement
            )

            if all_chorak_columns.count() == 4:
                chorak_plans = Plan.objects.filter(
                    organization=organization,
                    column__in=all_chorak_columns,
                    year=year
                )
                if chorak_plans.count() == 4:
                    total_value = sum(p.plan_value for p in chorak_plans)
                    yil_columns = StatementColumn.objects.filter(
                        status_plan=StatementColumn.PlanStatus.YILLIK,
                        statement=statement
                    )

                    for yil_column in yil_columns:
                        Plan.objects.update_or_create(
                            organization=organization,
                            statement=statement,
                            column=yil_column,
                            year=year,
                            defaults={'plan_value': total_value}
                        )


@extend_schema(tags=["Plan"])
class PlanListAPIView(generics.ListAPIView):
    queryset = Plan.objects.select_related('organization', 'column')
    serializer_class = PlanSerializer
    filterset_fields = ['column__id','statement','organization','year']

