from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from apps.reports.models import Report
from apps.reports.services import (
    aggregate_general_report,
    aggregate_national_report,
)
from apps.reports.services.individual_general_report import aggregate_individual_report
from apps.utils.services import RegionChoices


@receiver(post_save, sender=Report)
def handle_accepted_report(sender, instance: Report, created, **kwargs):
    print(">>> SIGNAL ISHLADI:", instance.id)

    if instance.status != Report.StatusChoices.ACCEPTED:
        return
    if not instance.is_report:
        return

    # 🎯 Individual reports only (not general/republic)
    if not instance.is_general and not instance.is_republic:
        # Avvalo individual umumlashtirishni yangilaymiz
        print(">>> [Individual] Individual Jami (org-level) yangilanmoqda")
        aggregate_individual_report(instance)

        print(">>> [Individual] Viloyat Jami chaqirilyapti")
        aggregate_general_report(
            statement=instance.statement,
            deadline=instance.deadline,
            region=instance.region
        )

        print(">>> [Individual] Respublika Jami chaqirilyapti")
        aggregate_national_report(
            statement=instance.statement,
            deadline=instance.deadline,
            region=RegionChoices.REPUBLIC
        )
        return

    # 🎯 If regional (viloyat) jami
    if instance.region and instance.is_general:
        print(">>> [General] Viloyat Jami chaqirilyapti")
        aggregate_general_report(
            statement=instance.statement,
            deadline=instance.deadline,
            region=instance.region
        )

        print(">>> [General] Respublika Jami chaqirilyapti")
        aggregate_national_report(
            statement=instance.statement,
            deadline=instance.deadline,
            region=RegionChoices.REPUBLIC
        )
        return



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

        # ✅ Faqat agar yana ACCEPTED report bo‘lsa, qayta aggregatsiya qilamiz
        if viloyat_qs.filter(status=Report.StatusChoices.ACCEPTED).exists():
            aggregate_general_report(
                statement=instance.statement,
                deadline=instance.deadline,
                region=instance.region,
            )

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

    # ✅ Faqat agar yana ACCEPTED report bo‘lsa, qayta aggregatsiya qilamiz
    if resp_qs.filter(status=Report.StatusChoices.ACCEPTED).exists():
        aggregate_national_report(
            statement=instance.statement,
            deadline=instance.deadline,
            region=RegionChoices.REPUBLIC,
        )