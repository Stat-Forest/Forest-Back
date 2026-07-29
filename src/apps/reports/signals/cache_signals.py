from django.db import transaction
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

from apps.reports.models import Report, ReportItem, ReportItemInner
from apps.reports.services.report_cache import bump_report_list_version


def bump_after_commit():
    transaction.on_commit(bump_report_list_version)


@receiver(post_save, sender=Report)
@receiver(post_delete, sender=Report)
def report_changed(sender, instance, **kwargs):
    bump_after_commit()


@receiver(post_save, sender=ReportItem)
@receiver(post_delete, sender=ReportItem)
def report_item_changed(sender, instance, **kwargs):
    bump_after_commit()


@receiver(post_save, sender=ReportItemInner)
@receiver(post_delete, sender=ReportItemInner)
def report_item_inner_changed(sender, instance, **kwargs):
    bump_after_commit()
