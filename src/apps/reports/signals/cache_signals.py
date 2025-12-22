from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.reports.models import Report, ReportItem, ReportItemInner
from apps.utils.cache_list import bump_cache_version


@receiver(post_save, sender=Report)
@receiver(post_delete, sender=Report)
def report_changed(sender, instance, **kwargs):
    bump_cache_version("report_list_version")


@receiver(post_save, sender=ReportItem)
@receiver(post_delete, sender=ReportItem)
def report_item_changed(sender, instance, **kwargs):
    bump_cache_version("report_list_version")


@receiver(post_save, sender=ReportItemInner)
@receiver(post_delete, sender=ReportItemInner)
def report_item_inner_changed(sender, instance, **kwargs):
    bump_cache_version("report_list_version")
