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


def is_access_token_revoked(token) -> bool:
    jti = token.get("jti") if hasattr(token, "get") else None
    return bool(jti and cache.get(_key(jti)))
