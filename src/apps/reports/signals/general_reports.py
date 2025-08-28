from django.db.models.signals import post_save, post_delete, pre_delete
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


@receiver(pre_delete, sender=Report)
def handle_delete_report(sender, instance: Report, **kwargs):
    print(">>>> REPORT DELETE SIGNAL", instance.id)

    if not instance.is_report:
        return

    # Hamma kerakli reportlarni oldindan bitta querysetga yig‘ib olamiz
    base_qs = Report.objects.filter(
        statement=instance.statement,
        deadline=instance.deadline,
    ).exclude(id=instance.id)

    # ========================
    # ✅ Individual Jami check
    # ========================
    if instance.organization:
        org_qs = base_qs.filter(
            organization=instance.organization,
            is_report=True,
            is_individual_general=False,
        )

        if not org_qs.exists():
            Report.objects.filter(
                statement=instance.statement,
                deadline=instance.deadline,
                organization=instance.organization,
                is_individual_general=True,
            ).delete()
            print("🗑️ Individual Jami o‘chirildi")

    # ====================
    # ✅ Viloyat Jami check
    # ====================
    if instance.region:
        viloyat_qs = base_qs.filter(
            region=instance.region,
            is_report=True,
            is_general=False,
            is_republic=False,
        )

        if not viloyat_qs.exists():
            Report.objects.filter(
                statement=instance.statement,
                deadline=instance.deadline,
                region=instance.region,
                is_general=True,
            ).delete()
            print("🗑️ Viloyat Jami o‘chirildi")

    # ========================
    # ✅ Respublika Jami check
    # ========================
    resp_qs = base_qs.filter(
        is_report=True,
        is_general=False,
        is_republic=False,
    )

    if not resp_qs.exists():
        Report.objects.filter(
            statement=instance.statement,
            deadline=instance.deadline,
            is_republic=True,
        ).delete()
        print("🗑️ Respublika Jami o‘chirildi")

    # =====================
    # ✅ Reaggregation
    # =====================
    aggregate_general_report(
        statement=instance.statement,
        deadline=instance.deadline,
        region=instance.region,
    )
    aggregate_national_report(
        statement=instance.statement,
        deadline=instance.deadline,
        region=RegionChoices.REPUBLIC,
    )

