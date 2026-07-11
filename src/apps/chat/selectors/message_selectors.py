from django.db.models import QuerySet

from apps.chat.models.chat import Message, Conversation


def get_recent_messages(
    *,
    conversation: Conversation,
    limit: int = 50,
) -> QuerySet[Message]:
    """
    Return latest messages of conversation.

    Ordered from oldest to newest.
    """

    message_ids = (
        Message.objects
        .filter(
            conversation=conversation,
        )
        .order_by("-created_at")
        .values_list(
            "id",
            flat=True,
        )[:limit]
    )

    return (
        Message.objects
        .filter(
            id__in=message_ids,
        )
        .select_related(
            "sender",
        )
        .order_by(
            "created_at",
        )
    )


def get_conversation_messages(
    conversation: Conversation,
) -> QuerySet[Message]:
    """
    Return all messages of conversation.
    """

    return (
        Message.objects
        .filter(conversation=conversation)
        .select_related("sender")
        .order_by("created_at")
    )


def get_last_message(
    conversation: Conversation,
) -> Message | None:
    """
    Return last message.
    """

    return (
        Message.objects
        .filter(conversation=conversation)
        .select_related("sender")
        .order_by("-created_at")
        .first()
    )


def get_unread_messages(
    conversation: Conversation,
    user,
) -> QuerySet[Message]:
    """
    Return unread messages for user.
    """

    return (
        Message.objects
        .filter(
            conversation=conversation,
            is_read=False,
        )
        .exclude(sender=user)
    )


def get_unread_count(
    conversation: Conversation,
    user,
) -> int:
    """
    Count unread messages.
    """

    return (
        get_unread_messages(
            conversation,
            user,
        )
        .count()
    )