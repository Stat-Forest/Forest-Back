"""
"O'rmon kadastri va monitoringi" bo'limi (Statement parent) — Ijara billing
rollari (`billing_user`, `billing_super`) stat'da faqat shu bo'limni (read-only) ko'radi.

Kadastr parent = `Statement(parent=None, is_used=True)`, nomi (uz/ru, apostrof va
bo'sh joylarsiz, kichik harf) `ormonkadastr`, `урмонкадастр` yoki `лесн`+`кадастр`ni o'z
ichiga oladi.
"""
import re

from django.core.cache import cache

KADASTR_CACHE_KEY = "reports:kadastr_parent_id"
KADASTR_CACHE_TIMEOUT = 60 * 60
_NOT_FOUND = "-"
_STRIP_RE = re.compile(r"[\s'`ʻʼ‘’ʹ´\"]+")


def normalize_statement_name(name: str | None) -> str:
    return _STRIP_RE.sub("", (name or "")).lower()


def is_kadastr_name(name: str | None) -> bool:
    value = normalize_statement_name(name)
    if not value:
        return False
    return (
        "ormonkadastr" in value
        or "урмонкадастр" in value
        or "ўрмонкадастр" in value
        or ("лесн" in value and "кадастр" in value)
    )


def _find_kadastr_parent_id():
    from apps.reports.models import Statement

    candidates = Statement.objects.filter(parent__isnull=True, is_used=True).order_by("created_at")
    for statement in candidates.only("id", "name", "name_uz", "name_ru"):
        names = (statement.name, getattr(statement, "name_uz", None), getattr(statement, "name_ru", None))
        if any(is_kadastr_name(name) for name in names):
            return statement.id
    return None


def get_kadastr_parent_id():
    """Kadastr parent Statement ID (topilmasa None). 1 soat cache."""
    cached = cache.get(KADASTR_CACHE_KEY)
    if cached is not None:
        return None if cached == _NOT_FOUND else cached
    found = _find_kadastr_parent_id()
    cache.set(KADASTR_CACHE_KEY, found or _NOT_FOUND, KADASTR_CACHE_TIMEOUT)
    return found


def get_kadastr_parent():
    """Kadastr parent `Statement` obyekti yoki None."""
    from apps.reports.models import Statement

    parent_id = get_kadastr_parent_id()
    if parent_id is None:
        return None
    return Statement.objects.filter(id=parent_id).first()


def invalidate_kadastr_cache() -> None:
    cache.delete(KADASTR_CACHE_KEY)


def is_kadastr_child(statement_id) -> bool:
    """Statement (hisobot formasi) kadastr parent'ning bolasimi."""
    from django.core.exceptions import ValidationError

    from apps.reports.models import Statement

    parent_id = get_kadastr_parent_id()
    if parent_id is None or not statement_id:
        return False
    try:
        return Statement.objects.filter(id=statement_id, parent_id=parent_id).exists()
    except (ValueError, ValidationError):
        return False
