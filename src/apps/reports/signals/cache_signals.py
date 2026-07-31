from django.db import transaction
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

from apps.reports.models import Report, ReportItem, ReportItemInner
from apps.reports.services.report_cache import (
    bump_report_list_version,
    invalidate_filtered_cache_for_statement,
)


def bump_after_commit():
    transaction.on_commit(bump_report_list_version)


def invalidate_filtered_after_commit(statement_id):
    """Signal-triggered: shu statement uchun filtered cache tozalash."""
    if statement_id:
        transaction.on_commit(
            lambda: invalidate_filtered_cache_for_statement(statement_id)
        )


@receiver(post_save, sender=Report)
@receiver(post_delete, sender=Report)
def report_changed(sender, instance, **kwargs):
    bump_after_commit()
    invalidate_filtered_after_commit(getattr(instance, "statement_id", None))


@receiver(post_save, sender=ReportItem)
@receiver(post_delete, sender=ReportItem)
def report_item_changed(sender, instance, **kwargs):
    bump_after_commit()
    report = getattr(instance, "report", None)
    if report:
        invalidate_filtered_after_commit(getattr(report, "statement_id", None))


@receiver(post_save, sender=ReportItemInner)
@receiver(post_delete, sender=ReportItemInner)
def report_item_inner_changed(sender, instance, **kwargs):
    bump_after_commit()
    report_item = getattr(instance, "report_item", None)
    if report_item:
        report = getattr(report_item, "report", None)
        if report:
            invalidate_filtered_after_commit(getattr(report, "statement_id", None))

