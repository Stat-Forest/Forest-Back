from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

from rest_framework_simplejwt.exceptions import (
    InvalidToken,
    TokenError,
)
from rest_framework_simplejwt.tokens import (
    AccessToken,
    UntypedToken,
)

from apps.users.models import CustomUser



@database_sync_to_async
def get_user_from_token(token: str):
    """
    Validate JWT token and return authenticated user.

    Returns:
        CustomUser | AnonymousUser
    """

    try:
        UntypedToken(token)

        payload = AccessToken(token)

        return CustomUser.objects.only(
            "id",
            "is_active",
        ).get(
            pk=payload["user_id"],
            is_active=True,
        )

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