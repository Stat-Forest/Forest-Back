from django.conf import settings
from django.utils import timezone

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed

from apps.authentications.service.role_access import check_role_path_access
from apps.authentications.service.token_denylist import is_access_token_revoked


class CustomJWTAuthentication(JWTAuthentication):
    """
    JWT auth + inactivity timeout.

    Parolni tiklash tokeni (`pwd_reset` claim) faqat
    `allow_password_reset_token = True` bo'lgan view'larda qabul qilinadi,
    aks holda u 10 daqiqa davomida to'liq access token bo'lib ishlar edi.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, validated_token = result

        # Logout qilingan token (muddati tugamagan bo'lsa ham) — yaroqsiz
        if is_access_token_revoked(validated_token):
            raise InvalidToken("Sessiya tugatilgan. Qayta login qiling.")

        if validated_token.get("pwd_reset"):
            view = (getattr(request, "parser_context", None) or {}).get("view")
            if not getattr(view, "allow_password_reset_token", False):
                raise InvalidToken("Parolni tiklash tokeni bu amal uchun yaroqsiz.")

        # Rol bo'yicha URL (va metod) cheklovi: support_admin, billing rollari
        check_role_path_access(user, request.path, request.method)

        return user, validated_token

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        if not user.is_active:
            raise AuthenticationFailed("Foydalanuvchi faol emas.", code="user_inactive")

        timeout_seconds = getattr(settings, "SESSION_INACTIVITY_TIMEOUT_SECONDS", 900)
        touch_interval_seconds = getattr(settings, "SESSION_ACTIVITY_TOUCH_INTERVAL_SECONDS", 60)
        now = timezone.now()

        if user.last_activity:
            inactivity_seconds = (now - user.last_activity).total_seconds()
            if inactivity_seconds > timeout_seconds:
                raise InvalidToken("Sessiya faol bo‘lmagani sabab tugatilgan. Qayta login qiling.")

            if inactivity_seconds >= touch_interval_seconds:
                user.last_activity = now
                user.save(update_fields=["last_activity"])
        else:
            user.last_activity = now
            user.save(update_fields=["last_activity"])

        return user