"""
Billing ma'lumotlari doirasi (scope).

    billing_xojalik_ids(user) -> set[UUID] | None    None = cheklovsiz
    is_billing_writer(user) -> bool
    can_write_xojalik(user, xojalik_id) -> bool

Qoidalar:
- `billing_user` (superuser emas) — faqat `BillingUserAccess.xojaliklar`
  doirasini ko'radi va faqat shu doirada yozadi; biriktirilmagan bo'lsa — hech narsa.
- `billing_super`, `super_admin`, superuser — hammasini ko'radi va yozadi.
- boshqa rollar — hammasini ko'radi (faqat o'qish).
"""
import uuid

from apps.users.models import CustomUser

WRITER_ROLES = {CustomUser.Role.BILLING_USER, CustomUser.Role.BILLING_SUPER, CustomUser.Role.SUPER_ADMIN}
BILLING_ROLES = {CustomUser.Role.BILLING_USER, CustomUser.Role.BILLING_SUPER}
# Ijarachi shaxsiy ma'lumotlari (PINFL, pasport, telefon, manzil) ko'rinadigan rollar (audit A4).
# Qolgan rollar billing monitoringini maskalangan holda ko'radi; ro'yxat/eksport/fayllar yopiq.
PII_ROLES = BILLING_ROLES | {CustomUser.Role.SUPER_ADMIN, CustomUser.Role.RAHBARIYAT}
NOT_ASSIGNED_MESSAGE = "Bu xo'jalik sizga biriktirilmagan"

_CACHE_ATTR = "_billing_xojalik_ids_cache"


def _is_authenticated(user) -> bool:
    return bool(user and getattr(user, "is_authenticated", False))


def is_billing_role(user) -> bool:
    """`billing_user` yoki `billing_super` (stat'da kadastr bo'limi bilan cheklangan rollar)."""
    return _is_authenticated(user) and getattr(user, "role", None) in BILLING_ROLES


def can_view_renter_pii(user) -> bool:
    return _is_authenticated(user) and (getattr(user, "role", None) in PII_ROLES or bool(user.is_superuser))


def is_scoped_billing_user(user) -> bool:
    return (
        _is_authenticated(user)
        and getattr(user, "role", None) == CustomUser.Role.BILLING_USER
        and not getattr(user, "is_superuser", False)
    )


def billing_xojalik_ids(user):
    """Ruxsat etilgan xo'jalik ID'lari to'plami yoki None (cheklovsiz)."""
    if not _is_authenticated(user):
        return set()
    if not is_scoped_billing_user(user):
        return None
    cached = getattr(user, _CACHE_ATTR, None)
    if cached is not None:
        return cached
    from apps.billing.models import BillingUserAccess

    ids = set(
        BillingUserAccess.xojaliklar.through.objects.filter(billinguseraccess__user_id=user.pk)
        .values_list("xojalik_id", flat=True)
    )
    setattr(user, _CACHE_ATTR, ids)
    return ids


def scope_queryset(queryset, user, field: str = "xojalik_id"):
    """`queryset`ni foydalanuvchi doirasi bo'yicha cheklaydi (`field__in`)."""
    ids = billing_xojalik_ids(user)
    if ids is None:
        return queryset
    if not ids:
        return queryset.none()
    return queryset.filter(**{f"{field}__in": ids})


def is_billing_writer(user) -> bool:
    return _is_authenticated(user) and (getattr(user, "role", None) in WRITER_ROLES or bool(user.is_superuser))


def _as_uuid(value):
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def can_write_xojalik(user, xojalik_id) -> bool:
    if not is_billing_writer(user):
        return False
    ids = billing_xojalik_ids(user)
    if ids is None:
        return True
    return _as_uuid(xojalik_id) in ids


def billing_organization_ids(user):
    """
    Stat kadastr bo'limidagi hisobot/hujjatlar uchun tashkilot doirasi:
    `billing_super` -> None (hammasi); `billing_user` -> o'z tashkiloti ∪
    biriktirilgan xo'jaliklarning `Xojalik.organization`i (bo'sh to'plam — hech narsa).
    """
    if not _is_authenticated(user):
        return set()
    if not is_scoped_billing_user(user):
        return None
    from apps.billing.models import Xojalik

    org_ids = set(
        Xojalik.objects.filter(id__in=billing_xojalik_ids(user), organization__isnull=False)
        .values_list("organization_id", flat=True)
    )
    if user.organization_id:
        org_ids.add(user.organization_id)
    return org_ids
