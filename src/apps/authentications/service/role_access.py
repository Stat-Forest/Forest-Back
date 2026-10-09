"""
Rol bo'yicha URL cheklovi — view'lardagi permission'lardan tashqari,
har bir autentifikatsiya qilingan so'rovda (CustomJWTAuthentication) ishlaydi.

Kiberxavfsizlik markazi topilmasi (CWE-862): "Support admin" foydalanuvchisi
hisobot va statistika endpointlariga murojaat qila olardi — chunki ko'p
view'lar faqat IsAuthenticated bilan himoyalangan. Bu ro'yxat o'sha
bo'shliqni markazlashgan holda yopadi: support_admin faqat chat, auth,
bildirishnoma va interfeys uchun zarur ma'lumotnomalarga kiradi.

Ikki xil qoida:
- deny/allow (support_admin): `deny` prefikslari taqiqlanadi, `allow` prefikslari undan istisno.
- allow-list (`"mode": "allowlist"` — billing_user, billing_super): `/api/v1/` ostidagi hamma
  narsa yopiq, faqat `allow` prefikslari va `allow_exact` aniq yo'llari ochiq; yozish
  (POST/PUT/PATCH/DELETE) faqat `write_allow` prefikslarida.
"""
from django.conf import settings
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS

API_PREFIX = "/api/v1/"

# Ijara billing rollari: billing bo'limi (o'qish/yozish) + stat'ning "O'rmon kadastri
# va monitoringi" bo'limi (faqat o'qish). Kadastr bilan cheklash view'larda.
BILLING_ROLE_RULES = {
    "mode": "allowlist",
    "allow": [
        "/api/v1/billing/",
        "/api/v1/authentications/",
        "/api/v1/chats/",
        "/api/v1/reports/statements/",
        "/api/v1/reports/statement-columns/",
        "/api/v1/reports/deadlines/",
        "/api/v1/reports/filtered-general/",
        "/api/v1/reports/individual/",
        "/api/v1/reports/export-excel/",
        "/api/v1/reports/users/",
        "/api/v1/general/land-documents/",
        "/api/v1/general/notifications/",
        "/api/v1/general/announcements/",
        "/api/v1/statistics/monitor-forest-uzlashtirish/",
    ],
    "allow_exact": [
        "/api/v1/reports/",
    ],
    "write_allow": [
        "/api/v1/billing/",
        "/api/v1/authentications/",
        "/api/v1/chats/",
        "/api/v1/reports/export-excel/",
    ],
}

DEFAULT_ROLE_PATH_RULES = {
    "support_admin": {
        "deny": [
            "/api/v1/reports/",
            "/api/v1/statistics/",
            "/api/v1/sum/",
            "/api/v1/information-analytical/",
            "/api/v1/report_admin_stat/",
            "/api/v1/general/land-documents/",
            "/api/v1/general/handbooks/",
            "/api/v1/e_imzo/save-pkcs7/",
            "/api/v1/e_imzo/verify-pkcs7/",
        ],
        "allow": [
            # support admin interfeysi uchun kerak (shakl/foydalanuvchi nomlari)
            "/api/v1/reports/statements/",
            "/api/v1/reports/users/",
            # ochiq (login sahifasi) statistikasi
            "/api/v1/reports/login-stat-deadlines/",
            "/api/v1/statistics/login-stats/",
        ],
    },
    # Ijara billing rollari — pastda (BILLING_ROLE_RULES, allow-list rejimi).
    "billing_user": BILLING_ROLE_RULES,
    "billing_super": BILLING_ROLE_RULES,
}


def _rules():
    return getattr(settings, "ROLE_PATH_RULES", DEFAULT_ROLE_PATH_RULES)


def _starts_with_any(path: str, prefixes) -> bool:
    return any(path.startswith(p) for p in prefixes)


def _allowlist_allows(rules: dict, path: str, method: str) -> bool:
    if not path.startswith(API_PREFIX):
        return True
    if not (path in rules.get("allow_exact", ()) or _starts_with_any(path, rules.get("allow", ()))):
        return False
    if (method or "GET").upper() in SAFE_METHODS:
        return True
    return _starts_with_any(path, rules.get("write_allow", ()))


def is_path_allowed_for_role(role: str, path: str, method: str = "GET") -> bool:
    rules = _rules().get(role)
    if not rules:
        return True
    if rules.get("mode") == "allowlist":
        return _allowlist_allows(rules, path, method)
    if _starts_with_any(path, rules.get("allow", ())):
        return True
    return not _starts_with_any(path, rules.get("deny", ()))


def check_role_path_access(user, path: str, method: str = "GET") -> None:
    role = getattr(user, "role", None)
    if getattr(user, "is_superuser", False) or not role:
        return
    if not is_path_allowed_for_role(role, path, method):
        raise PermissionDenied("Sizning rolingiz uchun bu bo'limga ruxsat yo'q.")
