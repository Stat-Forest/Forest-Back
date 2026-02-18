from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from apps.reports.models import StatementColumn


CACHE_KEY_PREFIXES = [
    "statement_column_tree_v1:",
    "statement_column_tree:",
]

LANGS = ["uz", "ru"]


def _clear_statement_column_cache(statement_id=None):
    # 1️⃣ Registry orqali tozalash (mavjud bo'lsa)
    for prefix in CACHE_KEY_PREFIXES:
        registry_key = f"{prefix}__registry__"
        all_keys: set = cache.get(registry_key) or set()

        if statement_id:
            sid = str(statement_id)
            keys_to_delete = {k for k in all_keys if f"statement={sid}:" in k}
        else:
            keys_to_delete = set(all_keys)

        if keys_to_delete:
            cache.delete_many(list(keys_to_delete))
            all_keys -= keys_to_delete
            if all_keys:
                cache.set(registry_key, all_keys, timeout=60 * 60 * 24)
            else:
                cache.delete(registry_key)

    # 2️⃣ Registry bo'sh yoki ishlamagan bo'lsa — to'g'ridan cache key yasab o'chiramiz
    if statement_id:
        sid = str(statement_id)
        direct_keys = []
        for prefix in CACHE_KEY_PREFIXES:
            for lang in LANGS:
                for is_user_input in ["", "True", "False"]:
                    key = f"{prefix}lang={lang}:statement={sid}:is_user_input={is_user_input}"
                    direct_keys.append(key)
        cache.delete_many(direct_keys)


@receiver(post_save, sender=StatementColumn)
def on_statement_column_save(sender, instance, **kwargs):
    _clear_statement_column_cache(statement_id=instance.statement_id)


@receiver(post_delete, sender=StatementColumn)
def on_statement_column_delete(sender, instance, **kwargs):
    _clear_statement_column_cache(statement_id=instance.statement_id)