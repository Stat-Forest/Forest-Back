from django.dispatch import receiver
from django.core.cache import caches
from django.db.models.signals import post_save, post_delete

from apps.general.models import Organization, Announcement


# ======================================================
# Clear organization list cache when data changes
# Triggered after create, update, or delete operations
# ======================================================
@receiver([post_save, post_delete], sender=Organization)
def clear_organization_cache(sender, **kwargs):
    redis_cache = caches['default']
    redis_cache.delete_pattern('organization_list_cache:*')


# ======================================================
# Clear active announcements cache when announcements
# are created, updated, or deleted.
# This ensures users always receive fresh data.
# ======================================================
@receiver([post_save, post_delete], sender=Announcement)
def clear_announcement_cache(sender, **kwargs):
    redis_cache = caches['default']

    # Cache key used in AnnouncementListAPIView
    redis_cache.delete("active_announcements")
