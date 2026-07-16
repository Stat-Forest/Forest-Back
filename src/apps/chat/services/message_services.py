from django.db import transaction
from django.utils import timezone

from apps.chat.exceptions import (
    ConversationAccessDenied,
    ConversationAlreadyClosed,
    ConversationNotFound, EmptyMessage,
)
from apps.chat.models import Conversation, Message
from apps.chat.selectors.conversation_selectors import (
    get_conversation_for_update, get_conversation_by_id,
)
from apps.chat.websocket.chat_serializers import MessageSerializer
from apps.users.models import CustomUser


def get_conversation_or_raise(
    *,
    conversation_id: str,
) -> Conversation:
    """
    Return conversation or raise exception.
    """

    conversation = get_conversation_by_id(
        conversation_id,
    )

    if conversation is None:
        raise ConversationNotFound(
            "Conversation not found."
        )

    return conversation


def can_connect_to_conversation(
    *,
    conversation: Conversation,
    user: CustomUser,
) -> None:
    """
    Validate websocket connection permissions.

    Allowed:

        • conversation owner

        • assigned support admin
    """

    if user.id == conversation.user_id:
        return

    if user.id == conversation.assigned_to_id:
        return

    raise ConversationAccessDenied(
        "You don't have permission to access this conversation."
    )


def _validate_conversation_access(
    *,
    conversation: Conversation,
    user: CustomUser,
) -> None:
    """
    Validate whether user has access to VIEW/READ this conversation.
    Conversation status does NOT matter here — closed conversations
    remain readable (history should never be blocked).
    """
    if user.id == conversation.user_id:
        return

    if user.id == conversation.assigned_to_id:
        return

    raise ConversationAccessDenied(
        "You don't have access to this conversation."
    )


def _validate_sender_access(
    *,
    conversation: Conversation,
    sender: CustomUser,
) -> None:
    """
    Validate whether sender can send a NEW message to this conversation.
    Closed conversations cannot receive new messages.
    """
    if conversation.status == Conversation.Status.CLOSED:
        raise ConversationAlreadyClosed(
            "Conversation already closed."
        )

    _validate_conversation_access(
        conversation=conversation,
        user=sender,
    )


@transaction.atomic
def send_message(
        *,
        conversation_id: str,
        sender: CustomUser,
        text: str,
) -> Message:
    """
    Create a new immutable message.
    """

    try:
        conversation = get_conversation_for_update(
            conversation_id
        )

    except Conversation.DoesNotExist:
        raise ConversationNotFound(
            "Conversation not found."
        )

    _validate_sender_access(
        conversation=conversation,
        sender=sender,
    )

    text = text.strip()
    if not text:
        raise EmptyMessage(
            "Message cannot be empty."
        )

    now = timezone.now()

    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        text=text,
        created_by=sender,
    )

    conversation.last_message_at = now
    conversation.updated_by = sender

    conversation.save(
        update_fields=[
            "last_message_at",
            "updated_by",
            "updated_at",
        ]
    )

    return message


def serialize_message(*, message: Message) -> dict:
    """
    Serialize message for websocket payload.
    """
    return MessageSerializer(
        message,
    ).data


@transaction.atomic
def mark_conversation_as_read(
        *,
        conversation_id: str,
        user: CustomUser,
) -> int:
    """
    Mark all unread messages as read for current user.

    Returns:
        Number of messages that were marked as read.
    """

    try:
        conversation = get_conversation_for_update(
            conversation_id
        )

    except Conversation.DoesNotExist:
        raise ConversationNotFound(
            "Conversation not found."
        )

    _validate_conversation_access(
        conversation=conversation,
        user=user,
    )

    updated_count = (
        Message.objects
        .filter(
            conversation=conversation,
            is_read=False,
        )
        .exclude(
            sender=user,
        )
        .update(
            is_read=True,
            updated_by=user,
        )
    )

    return updated_count
