"""
Rol bo'yicha URL cheklovi — view'lardagi permission'lardan tashqari,
har bir autentifikatsiya qilingan so'rovda (CustomJWTAuthentication) ishlaydi.

Kiberxavfsizlik markazi topilmasi (CWE-862): "Support admin" foydalanuvchisi
hisobot va statistika endpointlariga murojaat qila olardi — chunki ko'p
view'lar faqat IsAuthenticated bilan himoyalangan. Bu ro'yxat o'sha
bo'shliqni markazlashgan holda yopadi: support_admin faqat chat, auth,
bildirishnoma va interfeys uchun zarur ma'lumotnomalarga kiradi.

Qoida: `deny` prefikslari taqiqlanadi, `allow` prefikslari undan istisno.
"""
from django.conf import settings
from rest_framework.exceptions import PermissionDenied

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
}


def _rules():
    return getattr(settings, "ROLE_PATH_RULES", DEFAULT_ROLE_PATH_RULES)


def is_path_allowed_for_role(role: str, path: str) -> bool:
    rules = _rules().get(role)
    if not rules:
        return True
    if any(path.startswith(p) for p in rules.get("allow", ())):
        return True
    return not any(path.startswith(p) for p in rules.get("deny", ()))


def check_role_path_access(user, path: str) -> None:
    role = getattr(user, "role", None)
    if getattr(user, "is_superuser", False) or not role:
        return
    if not is_path_allowed_for_role(role, path):
        raise PermissionDenied("Sizning rolingiz uchun bu bo'limga ruxsat yo'q.")
