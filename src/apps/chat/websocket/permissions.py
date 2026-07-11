from apps.chat.exceptions import (
    ConversationAccessDenied,
    SupportPermissionDenied,
)
from apps.chat.models import Conversation
from apps.users.models import CustomUser


class BasePermission:
    """
    Base class for websocket permissions.
    """

    @classmethod
    async def check(cls, **kwargs):
        raise NotImplementedError


class IsAuthenticated(BasePermission):
    """
    Ensure websocket user is authenticated.
    """

    @classmethod
    async def check(
        cls,
        *,
        user: CustomUser,
    ) -> None:
        if not user.is_authenticated:
            raise ConversationAccessDenied(
                "Authentication required."
            )


class CanAccessConversation(BasePermission):
    """
    Validate whether user can open this conversation.

    Rules

    - Conversation owner can access.

    - Any SupportAdmin can access.

      This is required because a support administrator
      must be able to open NEW conversations before
      assigning them to himself.
    """

    SUPPORT_GROUP = "SupportAdmin"

    @classmethod
    async def check(
        cls,
        *,
        user: CustomUser,
        conversation: Conversation,
    ) -> None:

        if conversation.user_id == user.id:
            return

        if user.groups.filter(name=cls.SUPPORT_GROUP).exists():
            return

        raise ConversationAccessDenied(
            "You do not have access to this conversation."
        )


class CanSendMessage(BasePermission):
    """
    Validate whether user can send message.

    Rules

    User:
        Can send only inside his own conversation.

    SupportAdmin:
        Can send only if conversation is assigned to him.
    """

    SUPPORT_GROUP = "SupportAdmin"

    @classmethod
    async def check(
        cls,
        *,
        user: CustomUser,
        conversation: Conversation,
    ) -> None:

        if conversation.user_id == user.id:
            return

        if user.groups.filter(name=cls.SUPPORT_GROUP).exists():

            if conversation.assigned_to_id != user.id:
                raise ConversationAccessDenied(
                    "Conversation belongs to another support administrator."
                )

            return

        raise ConversationAccessDenied(
            "You cannot send messages to this conversation."
        )


class CanCloseConversation(BasePermission):
    """
    Only assigned support administrator
    can close conversation.
    """

    SUPPORT_GROUP = "SupportAdmin"

    @classmethod
    async def check(
        cls,
        *,
        user: CustomUser,
        conversation: Conversation,
    ) -> None:

        if not user.groups.filter(
            name=cls.SUPPORT_GROUP,
        ).exists():
            raise SupportPermissionDenied(
                "Support administrator permissions required."
            )

        if conversation.assigned_to_id != user.id:
            raise ConversationAccessDenied(
                "Conversation belongs to another support administrator."
            )