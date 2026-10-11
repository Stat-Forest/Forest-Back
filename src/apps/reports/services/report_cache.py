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


def _filtered_version_key(statement_id) -> str:
    return f"{FILTERED_CACHE_PREFIX}:ver:{statement_id}"


def get_filtered_version(statement_id) -> int:
    v = cache.get(_filtered_version_key(statement_id))
    return int(v) if v is not None else DEFAULT_VERSION


def bump_filtered_version(statement_id):
    """Shu statement'ning filtered-general keshi eskiradi (Report save/delete'da)."""
    key = _filtered_version_key(statement_id)
    try:
        cache.incr(key)
    except Exception:
        cache.set(key, DEFAULT_VERSION + 1, timeout=None)


def get_filtered_cache_key(statement_id, deadline_id, lang, quarter=None):
    """Cache key for build_filtered_payload results (statement versiyasi bilan)."""
    return (
        f"{FILTERED_CACHE_PREFIX}:v{get_filtered_version(statement_id)}:"
        f"{statement_id}:{deadline_id}:{lang}:{quarter or 'all'}"
    )


def get_cached_filtered_payload(statement_id, deadline_id, lang, quarter=None):
    """Return cached payload or None."""
    key = get_filtered_cache_key(statement_id, deadline_id, lang, quarter)
    return cache.get(key)


def set_cached_filtered_payload(statement_id, deadline_id, lang, quarter, payload):
    """Store payload in Redis."""
    key = get_filtered_cache_key(statement_id, deadline_id, lang, quarter)
    cache.set(key, payload, timeout=FILTERED_CACHE_TIMEOUT)


def invalidate_filtered_cache_for_statement(statement_id):
    """Eski nom — endi versiya oshiriladi (Redis KEYS pattern'siz)."""
    bump_filtered_version(statement_id)
