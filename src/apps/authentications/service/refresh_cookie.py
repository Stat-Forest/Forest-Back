"""
Refresh token HttpOnly cookie'da (audit A5).

Frontend refresh tokenni localStorage/oddiy cookie'ga yozmaydi — XSS yoki
uchinchi tomon skripti uni o'qiy olmaydi. Cookie faqat /api/v1/authentications/
yo'liga yuboriladi (refresh, logout); API so'rovlari avvalgidek Bearer access
token bilan. stat-urmon.uz -> api.stat-urmon.uz bir "site" (SameSite=Lax yetarli).
"""
from django.conf import settings

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/authentications/"


def _max_age() -> int:
    lifetime = settings.SIMPLE_JWT.get("REFRESH_TOKEN_LIFETIME")
    return int(lifetime.total_seconds()) if lifetime else 24 * 3600


def set_refresh_cookie(response, refresh: str):
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=_max_age(),
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
    )
    return response


def clear_refresh_cookie(response):
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, samesite="Lax")
    return response


def refresh_from_request(request) -> str | None:
    """Body'dagi `refresh` (eski mijozlar) yoki HttpOnly cookie."""
    data = getattr(request, "data", None) or {}
    return data.get("refresh") or request.COOKIES.get(REFRESH_COOKIE)
