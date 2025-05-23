from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.reports.models import Plan, StatementColumn
from django.db.models import Sum

@receiver([post_save, post_delete], sender=Plan)
def update_dependent_plans(sender, instance, **kwargs):
    plan = instance
    organization = plan.organization
    statement = plan.column.statement
    year = plan.year
    status = plan.column.status_plan

    chorak_map = {
        StatementColumn.PlanStatus.CHORAK_1: [StatementColumn.PlanStatus.YANVAR, StatementColumn.PlanStatus.FEVRAL, StatementColumn.PlanStatus.MART],
        StatementColumn.PlanStatus.CHORAK_2: [StatementColumn.PlanStatus.APREL, StatementColumn.PlanStatus.MAY, StatementColumn.PlanStatus.IYUN],
        StatementColumn.PlanStatus.CHORAK_3: [StatementColumn.PlanStatus.IYUL, StatementColumn.PlanStatus.AVGUST, StatementColumn.PlanStatus.SENTABR],
        StatementColumn.PlanStatus.CHORAK_4: [StatementColumn.PlanStatus.OKTABR, StatementColumn.PlanStatus.NOYABR, StatementColumn.PlanStatus.DEKABR],
    }

    # === Oylikdan chorakka
    for chorak_status, oy_statuslar in chorak_map.items():
        if status in oy_statuslar:
            oy_columns = StatementColumn.objects.filter(statement=statement, status_plan__in=oy_statuslar)
            oy_plans = Plan.objects.filter(organization=organization, column__in=oy_columns, year=year)
            if oy_plans.count() == 3:
                total = oy_plans.aggregate(total=Sum('plan_value'))['total']
                chorak_column = StatementColumn.objects.filter(statement=statement, status_plan=chorak_status).first()
                if chorak_column:
                    Plan.objects.update_or_create(
                        organization=organization,
                        column=chorak_column,
                        year=year,
                        defaults={'plan_value': total}
                    )

    # === Chorakdan yillikka
    all_chorak_columns = StatementColumn.objects.filter(statement=statement, status_plan__in=chorak_map.keys())
    chorak_plans = Plan.objects.filter(organization=organization, column__in=all_chorak_columns, year=year)
    if chorak_plans.count() == 4:
        total = chorak_plans.aggregate(total=Sum('plan_value'))['total']
        yil_column = StatementColumn.objects.filter(statement=statement, status_plan=StatementColumn.PlanStatus.YILLIK).first()
        if yil_column:
            Plan.objects.update_or_create(
                organization=organization,
                column=yil_column,
                year=year,
                defaults={'plan_value': total}
            )
