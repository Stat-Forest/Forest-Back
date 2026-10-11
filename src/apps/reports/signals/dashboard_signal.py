from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from apps.reports.models import Report
from apps.reports.services.report_cache import bump_report_list_version

DASHBOARD_VERSION_KEY = "dashboard:stats:ver"


def get_dashboard_version() -> int:
    v = cache.get(DASHBOARD_VERSION_KEY)
    if v is None:
        cache.set(DASHBOARD_VERSION_KEY, 1, timeout=None)
        return 1
    return int(v)


def bump_dashboard_version():
    try:
        cache.incr(DASHBOARD_VERSION_KEY)
    except Exception:
        cache.set(DASHBOARD_VERSION_KEY, 2, timeout=None)


@receiver(post_save, sender=Report, dispatch_uid="reports.dashboard_cache.save")
@receiver(post_delete, sender=Report, dispatch_uid="reports.dashboard_cache.delete")
def invalidate_dashboard_cache(sender, instance, **kwargs):
    """
    Versiya kaliti: barcha foydalanuvchilar keshi bir zumda eskiradi (TTL bilan
    o'zi o'chadi). Ilgari har Report save'ida 4 ta CustomUser so'rovi va har
    foydalanuvchi uchun alohida DELETE edi.
    """
    bump_dashboard_version()
    # Bosh sahifa overview keshi ham shu versiyaga bog'liq (dashboard_overview)
    bump_report_list_version()
