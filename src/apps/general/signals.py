from django.dispatch import receiver
from django.core.cache import caches
from django.db.models.signals import post_save, post_delete

from apps.general.models import LandManagement, Organization, Announcement, Handbook, LandDocument

# ======================================================
# Use default Redis cache backend
# ======================================================
redis_cache = caches["default"]


# ======================================================
# Organization Cache Invalidation
# ------------------------------------------------------
# Clears all organization list caches after any change
# ======================================================
@receiver([post_save, post_delete], sender=Organization)
def clear_organization_cache(sender, instance, **kwargs):
    redis_cache.delete_pattern("organization_list_cache:*")


# ======================================================
# Announcement Cache Invalidation
# ------------------------------------------------------
# Ensures active announcements cache is always fresh
# ======================================================
@receiver([post_save, post_delete], sender=Announcement)
def clear_announcement_cache(sender, instance, **kwargs):
    redis_cache.delete("active_announcements")


# ======================================================
# Handbook Cache Invalidation
# ------------------------------------------------------
# Clears handbook cache when data changes
# ======================================================
@receiver([post_save, post_delete], sender=Handbook)
def clear_handbook_cache(sender, instance, **kwargs):
    redis_cache.delete("visible_handbooks")


# ======================================================
# LandDocument Cache Invalidation
# ------------------------------------------------------
# Clears land document cache when documents change
# ======================================================
@receiver([post_save, post_delete], sender=LandDocument)
def clear_land_document_cache(sender, instance, **kwargs):
    redis_cache.delete("land_documents")



# ======================================================
# Clears LandManagement cache when data changes
# ======================================================
@receiver([post_save, post_delete], sender=LandManagement)
def clear_land_management_cache(sender, instance, **kwargs):
    """
    Clears LandManagement summary cache when any LandManagement item changes.
    """
    redis_cache.delete_pattern("land_management_summary:*")