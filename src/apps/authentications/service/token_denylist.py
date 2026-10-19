"""
Access token'larni muddati tugashidan oldin bekor qilish (logout).

JWT o'z-o'zidan bekor qilinmaydi: logout'dan keyin ham access token muddati
(15 daqiqa) tugaguncha ishlayverardi (Kiberxavfsizlik markazi, CWE-613).
Logout'da tokenning `jti` si cache'ga yoziladi va har bir so'rovda
(HTTP va WebSocket) tekshiriladi. Yozuv tokenning qolgan muddaticha
saqlanadi, undan keyin token baribir yaroqsiz.
"""
from django.core.cache import cache
from django.utils import timezone

PREFIX = "jwt_revoked:"


def _key(jti: str) -> str:
    return f"{PREFIX}{jti}"


def revoke_access_token(token) -> None:
    """`token` — tekshirilgan simplejwt Token obyekti (jti va exp bilan)."""
    jti = token.get("jti")
    exp = token.get("exp")
    if not jti:
        return
    ttl = 60
    if exp:
        ttl = max(int(exp - timezone.now().timestamp()), 1)
    cache.set(_key(jti), True, ttl)


def revoke_user_tokens_issued_before(user_id, cutoff_ts: int | None = None, ttl: int | None = None) -> None:
    """Parol o'zgarganda foydalanuvchining shu paytgacha berilgan BARCHA access
    tokenlari yaroqsiz bo'ladi (audit C3) — boshqa qurilmadagi sessiya ham."""
    # +1: iat soniyalarda — shu soniyada berilgan tokenlar ham yaroqsiz bo'lsin
    cutoff = int(cutoff_ts if cutoff_ts is not None else timezone.now().timestamp()) + 1
    if ttl is None:
        from django.conf import settings
        lifetime = settings.SIMPLE_JWT.get("ACCESS_TOKEN_LIFETIME")
        ttl = int(lifetime.total_seconds()) if lifetime else 900
    cache.set(f"{PREFIX}user_cutoff:{user_id}", cutoff, ttl + 60)


def is_access_token_revoked(token) -> bool:
    if not hasattr(token, "get"):
        return False
    jti = token.get("jti")
    if jti and cache.get(_key(jti)):
        return True
    user_id, iat = token.get("user_id"), token.get("iat")
    if user_id and iat is not None:
        cutoff = cache.get(f"{PREFIX}user_cutoff:{user_id}")
        if cutoff is not None and int(iat) < int(cutoff):
            return True
    return False
