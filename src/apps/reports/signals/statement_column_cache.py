"""
apps/reports/signals/statement_column_cache.py

StatementColumn qo'shilsa, o'chirilsa yoki o'zgartirilsa
barcha bog'liq cache kalitlari avtomatik tozalanadi.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from apps.reports.models import StatementColumn


CACHE_KEY_PREFIXES = [
    "statement_column_tree_v1:",  # StatementColumnTreeAPIView
    "statement_column_tree:",     # CorrectedStatementColumnTreeAPIView
]


def _clear_statement_column_cache(statement_id=None):
    for prefix in CACHE_KEY_PREFIXES:
        registry_key = f"{prefix}__registry__"
        all_keys: set = cache.get(registry_key) or set()

        if statement_id:
            sid = str(statement_id)  # ✅ UUID → str, type mismatch yo'q
            keys_to_delete = {k for k in all_keys if f"statement={sid}:" in k}
        else:
            keys_to_delete = set(all_keys)  # ✅ copy olamiz

        if keys_to_delete:
            cache.delete_many(list(keys_to_delete))  # ✅ list ga o'tkazamiz
            all_keys -= keys_to_delete
            if all_keys:
                cache.set(registry_key, all_keys, timeout=60 * 60 * 24)
            else:
                cache.delete(registry_key)


@receiver(post_save, sender=StatementColumn)
def on_statement_column_save(sender, instance, **kwargs):
    _clear_statement_column_cache(statement_id=instance.statement_id)


@receiver(post_delete, sender=StatementColumn)
def on_statement_column_delete(sender, instance, **kwargs):
    _clear_statement_column_cache(statement_id=instance.statement_id)