from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.db.models import signals

from apps.reports.models import Plan, StatementColumn

@receiver(post_save, sender=Plan)
def update_related_plans(sender, instance, created, **kwargs):
    if created:
        return

    organization = instance.organization
    year = instance.year
    statement = instance.statement
    column = instance.column

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

    signals.post_save.disconnect(update_related_plans, sender=Plan)

    try:
        with transaction.atomic():
            # Har bir chorak uchun yig'indini hisoblash
            for quarter_status, month_status_list in chorak_map.items():
                month_columns = list(
                    StatementColumn.objects.filter(
                        status_plan__in=month_status_list,
                        statement=statement
                    )
                )
                if len(month_columns) != 3:
                    continue

                month_plans = list(
                    Plan.objects.filter(
                        statement=statement,
                        organization=organization,
                        column__in=month_columns,
                        year=year
                    )
                )
                if len(month_plans) != 3:
                    continue

                total_value = sum(p.plan_value for p in month_plans)
                quarter_column = StatementColumn.objects.filter(
                    status_plan=quarter_status,
                    statement=statement
                ).first()

                if quarter_column:
                    Plan.objects.update_or_create(
                        organization=organization,
                        statement=statement,
                        column=quarter_column,
                        year=year,
                        defaults={'plan_value': total_value}
                    )

            # Yillikni hisoblash
            all_quarter_columns = StatementColumn.objects.filter(
                status_plan__in=chorak_map.keys(),
                statement=statement
            )

            if all_quarter_columns.count() == 4:
                quarter_plans = Plan.objects.filter(
                    statement=statement,
                    organization=organization,
                    column__in=all_quarter_columns,
                    year=year
                )
                if quarter_plans.count() == 4:
                    total_value = sum(p.plan_value for p in quarter_plans)
                    year_columns = StatementColumn.objects.filter(
                        status_plan=StatementColumn.PlanStatus.YILLIK,
                        statement=statement
                    )
                    for yil_column in year_columns:
                        Plan.objects.update_or_create(
                            organization=organization,
                            statement=statement,
                            column=yil_column,
                            year=year,
                            defaults={'plan_value': total_value}
                        )
    finally:
        # Signalni yana qayta ulab qo'yamiz
        signals.post_save.connect(update_related_plans, sender=Plan)
