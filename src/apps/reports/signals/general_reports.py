from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.reports.models import Report
from apps.reports.report_calculate import ALL_CALCULATORS
from apps.reports.services import (
    aggregate_general_report,
    aggregate_national_report,
)
from apps.utils.services import RegionChoices


@receiver(post_save, sender=Report)
def handle_accepted_report(sender, instance: Report, created, **kwargs):
    print(">>> SIGNAL ISHLADI:", instance.id)

    if instance.status != Report.StatusChoices.ACCEPTED:
        return

    if not instance.is_report:
        return

    # ✅ Hisoblash
    # statement_name = instance.statement.name_uz
    # calculate_func = ALL_CALCULATORS.get(statement_name)
    # if calculate_func:
    #     calculate_func(instance)

    # ✅ Region Jami (individual bo‘lmaganlar uchun)
    if instance.region:
        print(">>> Viloyat Jami chaqirilyapti")
        aggregate_general_report(
            statement=instance.statement,
            deadline=instance.deadline,
            region=instance.region
        )


        print(">>> Respublika Jami chaqirilyapti")
        aggregate_national_report(
            statement=instance.statement,
            deadline=instance.deadline,
            region=RegionChoices.REPUBLIC
        )
