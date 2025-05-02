from django.dispatch import receiver
from django.core.cache import caches
from apps.reports.models import Organization
from django.db.models.signals import post_save, post_delete

@receiver([post_save, post_delete], sender=Organization)
def clear_organization_cache(sender, **kwargs):
    redis_cache = caches['default']
    redis_cache.delete_pattern('organization_list_cache:*')