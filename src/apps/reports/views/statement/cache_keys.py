"""
Cache key management for statements
"""


def get_statement_list_cache_key(user_statement_id=None, lang='uz'):
    """
    Generate cache key for statement list
    Args:
        user_statement_id: User's statement ID if exists
        lang: Language code (uz, ru)
    """
    if user_statement_id:
        return f"statement_list:stmt_{user_statement_id}:lang_{lang}"
    return f"statement_list:all:lang_{lang}"


def get_statement_cache_key(statement_id):
    """Cache key for single statement"""
    return f"statement:id_{statement_id}"


def invalidate_statement_cache(statement_id=None):
    """
    Invalidate statement-related caches
    Args:
        statement_id: If provided, invalidate specific statement and related caches
    """
    from django.core.cache import cache

    # Barcha statement list cache'larini tozalash
    cache.delete_pattern("statement_list:*")

    # Agar aniq statement berilgan bo'lsa
    if statement_id:
        cache.delete(get_statement_cache_key(statement_id))