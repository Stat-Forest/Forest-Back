import logging

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from apps.reports.models import Report
from apps.reports.services import (
    aggregate_general_report,
    aggregate_national_report,
)
from apps.utils.services import RegionChoices

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Report, dispatch_uid="reports.handle_accepted_report")
def handle_accepted_report(sender, instance: Report, created, **kwargs):
    if instance.status != Report.StatusChoices.ACCEPTED:
        return
    if not instance.is_report:
        return
    # Yig'ma hisobotlar Celery'da (apps.reports.tasks.aggregation); qaysi
    # turdagi yig'ma kerakligi task ichida hal qilinadi.
    if (not instance.is_general and not instance.is_republic) or (instance.region and instance.is_general):
        from apps.reports.tasks.aggregation import schedule_report_totals
        schedule_report_totals(str(instance.id))


@receiver(pre_delete, sender=Report, dispatch_uid="reports.handle_delete_report")
def handle_delete_report(sender, instance: Report, **kwargs):
    logger.debug("report delete signal %s", instance.id)

    if not instance.is_report:
        return

    # Signal ni vaqtincha o'chiramiz — ichki .delete() chaqiruvlari
    # yana shu signalni ishga tushirib, RecursionError keltirib chiqarmasligi uchun.
    pre_delete.disconnect(sender=Report, dispatch_uid="reports.handle_delete_report")
    try:
        _handle_delete_report_inner(instance)
    finally:
        # Har qanday holatda signalni qayta ulaymiz
        pre_delete.connect(handle_delete_report, sender=Report, dispatch_uid="reports.handle_delete_report")


def _handle_delete_report_inner(instance: Report):
    """
    Report o'chirilganda bog'liq jami reportlarni tozalash.

    Bu funksiya signal ichidan chaqiriladi, lekin signal vaqtincha
    o'chirilgan bo'ladi — shuning uchun ichki .delete() chaqiruvlari
    rekursiyaga olib kelmaydi.
    """
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

    # ✅ Faqat agar yana ACCEPTED report bo‘lsa, qayta aggregatsiya qilamiz
    if resp_qs.filter(status=Report.StatusChoices.ACCEPTED).exists():
        aggregate_national_report(
            statement=instance.statement,
            deadline=instance.deadline,
            region=RegionChoices.REPUBLIC,
        )