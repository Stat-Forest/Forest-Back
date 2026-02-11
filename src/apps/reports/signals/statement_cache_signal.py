# apps/reports/signals/statement_signals.py
"""
Signal handlers for Statement model
Handle cache invalidation and other post-save/delete operations
"""
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.core.cache import cache

from apps.reports.models import Statement
from apps.reports.views.statement.cache_keys import invalidate_statement_cache


@receiver(post_save, sender=Statement)
def statement_post_save_handler(sender, instance, created, **kwargs):
    """
    Handle cache invalidation when statement is saved

    Args:
        sender: Statement model
        instance: Statement instance that was saved
        created: Boolean - True if new instance created
        **kwargs: Additional arguments
    """
    # Agar statement o'zgargan bo'lsa, barcha related cache'larni tozalash
    invalidate_statement_cache(instance.id)

    # Agar bu child statement bo'lsa, parent ham ta'sirlangan
    if instance.parent_id:
        invalidate_statement_cache(instance.parent_id)


@receiver(post_delete, sender=Statement)
def statement_post_delete_handler(sender, instance, **kwargs):
    """
    Handle cache invalidation when statement is deleted

    Args:
        sender: Statement model
        instance: Statement instance that was deleted
        **kwargs: Additional arguments
    """
    invalidate_statement_cache(instance.id)

    if instance.parent_id:
        invalidate_statement_cache(instance.parent_id)


@receiver(pre_delete, sender=Statement)
def statement_pre_delete_handler(sender, instance, **kwargs):
    """
    Handle operations before statement deletion
    Can be used for logging or additional cleanup

    Args:
        sender: Statement model
        instance: Statement instance about to be deleted
        **kwargs: Additional arguments
    """
    # Agar kerak bo'lsa, children cache'larini ham tozalash
    if hasattr(instance, 'children'):
        children_ids = instance.children.values_list('id', flat=True)
        for child_id in children_ids:
            invalidate_statement_cache(child_id)