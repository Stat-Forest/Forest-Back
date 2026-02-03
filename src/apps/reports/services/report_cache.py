from django.core.cache import cache

REPORT_LIST_VERSION_KEY = "reports:list:version"
DEFAULT_VERSION = 1


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
