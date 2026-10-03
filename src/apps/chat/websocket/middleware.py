from urllib.parse import parse_qs
from django.utils import timezone
from django.conf import settings

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

from rest_framework_simplejwt.exceptions import (
    InvalidToken,
    TokenError,
)
from rest_framework_simplejwt.tokens import AccessToken

from apps.users.models import CustomUser



@database_sync_to_async
def get_user_from_token(token: str):
    """
    Validate JWT token and return authenticated user.
    
    Also checks inactivity timeout to match CustomJWTAuthentication logic.

    Returns:
        CustomUser | AnonymousUser
    """

    try:
        # `AccessToken` imzo, muddat va token turini o'zi tekshiradi —
        # refresh token bu yerdan o'tolmaydi.
        payload = AccessToken(token)

        # Parolni tiklash tokeni chat uchun yaroqsiz
        if payload.get("pwd_reset"):
            return AnonymousUser()

        # `.only()` ishlatilmaydi: xabar serializatsiyasi first_name/
        # last_name/role ni o'qiydi va deferred maydonlar har bir xabar
        # uchun qo'shimcha so'rov keltirib chiqarardi.
        user = CustomUser.objects.get(
            pk=payload["user_id"],
            is_active=True,
        )

        # Inactivity timeout check (same as CustomJWTAuthentication)
        timeout_seconds = getattr(settings, "SESSION_INACTIVITY_TIMEOUT_SECONDS", 900)
        touch_interval_seconds = getattr(settings, "SESSION_ACTIVITY_TOUCH_INTERVAL_SECONDS", 60)
        now = timezone.now()

        if user.last_activity:
            inactivity_seconds = (now - user.last_activity).total_seconds()

            if inactivity_seconds > timeout_seconds:
                return AnonymousUser()

            # Faollikni yangilaymiz. Aks holda faqat WebSocket orqali
            # yozishayotgan foydalanuvchining sessiyasi "harakatsiz" deb
            # hisoblanib, keyingi ulanishda 4401 bilan rad etilardi.
            if inactivity_seconds >= touch_interval_seconds:
                user.last_activity = now
                user.save(update_fields=["last_activity"])
        else:
            user.last_activity = now
            user.save(update_fields=["last_activity"])

        return user

    except (
        TokenError,
        InvalidToken,
        CustomUser.DoesNotExist,
        KeyError,
    ):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    JWT authentication middleware.

    Expected connection:

        ws://host/ws/chat/<conversation_id>/?token=<access_token>
    """

    async def __call__(
        self,
        scope,
        receive,
        send,
    ):
        query_string = scope.get(
            "query_string",
            b"",
        ).decode()

        token = parse_qs(query_string).get(
            "token",
            [None],
        )[0]

        if token:
            scope["user"] = await get_user_from_token(token)
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(
            scope,
            receive,
            send,
        )


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(
        AuthMiddlewareStack(inner)
    )