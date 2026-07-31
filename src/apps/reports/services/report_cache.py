from django.core.cache import cache

REPORT_LIST_VERSION_KEY = "reports:list:version"
DEFAULT_VERSION = 1

FILTERED_CACHE_PREFIX = "filtered"
FILTERED_CACHE_TIMEOUT = 300  # 5 daqiqa


def get_report_list_version() -> int:
    v = cache.get(REPORT_LIST_VERSION_KEY)
    if v is None:
        cache.set(REPORT_LIST_VERSION_KEY, DEFAULT_VERSION, timeout=None)
        return DEFAULT_VERSION
    return int(v)


def bump_report_list_version():
    try:
        cache.incr(REPORT_LIST_VERSION_KEY)
    except Exception:
        cache.set(REPORT_LIST_VERSION_KEY, DEFAULT_VERSION + 1, timeout=None)


def get_filtered_cache_key(statement_id, deadline_id, lang, quarter=None):
    """Cache key for build_filtered_payload results."""
    return f"{FILTERED_CACHE_PREFIX}:{statement_id}:{deadline_id}:{lang}:{quarter or 'all'}"


def get_cached_filtered_payload(statement_id, deadline_id, lang, quarter=None):
    """Return cached payload or None."""
    key = get_filtered_cache_key(statement_id, deadline_id, lang, quarter)
    return cache.get(key)


def set_cached_filtered_payload(statement_id, deadline_id, lang, quarter, payload):
    """Store payload in Redis."""
    key = get_filtered_cache_key(statement_id, deadline_id, lang, quarter)
    cache.set(key, payload, timeout=FILTERED_CACHE_TIMEOUT)


def invalidate_filtered_cache_for_statement(statement_id):
    """
    Signal-triggered: o'zgarish bo'lganda shu statementga oid
    barcha filtered cache'larni tozalash.
    Pattern-based delete — language va quarter kombinatsiyalari ko'p
    bo'lganligi uchun, kalitlarni Redis'dan pattern bilan topamiz.
    """
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        # Redis key pattern: ":1:filtered:<statement_id>:*"
        # django_redis default prefix ":1:" qo'shadi
        pattern = f"*{FILTERED_CACHE_PREFIX}:{statement_id}:*"
        keys = conn.keys(pattern)
        if keys:
            conn.delete(*keys)
    except Exception:
        # Agar django_redis yo'q yoki Redis muammo — xatolikni yutamiz
        pass

