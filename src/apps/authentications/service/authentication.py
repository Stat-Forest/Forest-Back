from django.conf import settings
from django.utils import timezone

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed


class CustomJWTAuthentication(JWTAuthentication):
    """
    JWT auth + inactivity timeout.
    """

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