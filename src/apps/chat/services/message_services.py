from django.db import transaction
from django.utils import timezone

from apps.chat.exceptions import (
    ConversationAccessDenied,
    ConversationAlreadyClosed,
    ConversationNotFound,
    EmptyMessage,
    MessageTooLong,
)
from apps.chat.models import Conversation, Message
from apps.chat.models.chat import MAX_MESSAGE_LENGTH
from apps.chat.permissions import can_manage_support_chat
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


def _is_owner(conversation: Conversation, user: CustomUser) -> bool:
    return user.id is not None and user.id == conversation.user_id


def _is_assigned_admin(conversation: Conversation, user: CustomUser) -> bool:
    """
    `is not None` tekshiruvi shart: biriktirilmagan chatda
    `assigned_to_id` ham, `AnonymousUser.id` ham None bo'ladi va
    oddiy `==` solishtiruvi ruxsat berib yuborardi.
    """

    return (
        conversation.assigned_to_id is not None
        and user.id == conversation.assigned_to_id
    )


def validate_conversation_access(
    *,
    conversation: Conversation,
    user: CustomUser,
) -> None:
    """
    O'QISH ruxsati (tarixni ko'rish, websocket'ga ulanish).

    Ruxsat:
        • chat egasi
        • biriktirilgan support admin
        • istalgan support admin — navbatdagi NEW chatni ochib savolni
          o'qishi uchun (aks holda admin chatni ko'r-ko'rona olishga
          majbur bo'lardi)

    Chat holati bu yerda ahamiyatsiz — yopilgan chat tarixi ham
    o'qilaveradi.
    """

    if _is_owner(conversation, user):
        return

    if _is_assigned_admin(conversation, user):
        return

    if can_manage_support_chat(user):
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
    YOZISH ruxsati.

    DIQQAT: bu yerda `validate_conversation_access` ishlatilmaydi.
    O'qish ruxsati atayin kengroq (istalgan support admin), yozish esa
    tor bo'lib qolishi shart — aks holda biriktirilmagan admin istalgan
    chatga yozib yuborardi.

    Ruxsat: chat egasi yoki AYNAN biriktirilgan admin.
    Yopilgan chatga hech kim yoza olmaydi.
    """

    if conversation.status == Conversation.Status.CLOSED:
        raise ConversationAlreadyClosed(
            "Conversation already closed."
        )

    if _is_owner(conversation, sender):
        return

    if _is_assigned_admin(conversation, sender):
        return

    raise ConversationAccessDenied(
        "You cannot send messages to this conversation."
    )


def _clean_text(text) -> str:
    """
    Xabar matnini tekshirish va tozalash.

    Uzunlik aynan shu yerda tekshiriladi: modeldagi
    `MaxLengthValidator` faqat `full_clean()` da ishlaydi, uni esa
    `Message.objects.create()` chaqirmaydi.
    """

    if not isinstance(text, str):
        raise EmptyMessage(
            "Message cannot be empty."
        )

    text = text.strip()

    if not text:
        raise EmptyMessage(
            "Message cannot be empty."
        )

    if len(text) > MAX_MESSAGE_LENGTH:
        raise MessageTooLong(
            f"Message cannot be longer than {MAX_MESSAGE_LENGTH} characters."
        )

    return text


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

    text = _clean_text(text)

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

    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        text=text,
        created_by=sender,
    )

    conversation.last_message_at = message.created_at
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

    conversation = get_conversation_by_id(conversation_id)

    if conversation is None:
        raise ConversationNotFound(
            "Conversation not found."
        )

    validate_conversation_access(
        conversation=conversation,
        user=user,
    )

    return (
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
            updated_at=timezone.now(),
        )
    )
