from django.db.models import QuerySet, Q

from apps.chat.models.chat import Conversation
from apps.users.models import CustomUser


def get_accessible_conversation(
        *,
        conversation_id: str,
        user: CustomUser,
) -> Conversation | None:
    """
    Return conversation if current user
    has access to it.

    Access:
        - Conversation owner
        - Assigned support administrator
    """

    return (
        Conversation.objects
        .select_related(
            "user",
            "assigned_to",
        )
        .filter(
            id=conversation_id,
        )
        .filter(
            Q(user=user)
            |
            Q(assigned_to=user)
        )
        .first()
    )


def get_conversation_by_id(conversation_id: str) -> Conversation | None:
    """
    Return conversation by id.
    """

    try:
        return (
            Conversation.objects
            .select_related("user", "assigned_to")
            .get(id=conversation_id)
        )
    except Conversation.DoesNotExist:
        return None


def get_conversation_for_update(conversation_id: str) -> Conversation:
    """
    Used inside transaction.select_for_update().
    """

    return (
        Conversation.objects
        .select_for_update(of=("self",))
        .select_related("user", "assigned_to")
        .get(id=conversation_id)
    )


def get_user_active_conversation(user: CustomUser) -> Conversation | None:
    """
    Return user's active conversation.
    """

    return (
        Conversation.objects
        .select_related("assigned_to")
        .filter(
            user=user,
            status__in=[
                Conversation.Status.NEW,
                Conversation.Status.TAKEN,
            ]
        )
        .first()
    )


def get_user_conversations(user: CustomUser) -> QuerySet[Conversation]:
    """
    Return all conversations of user.
    """

    return (
        Conversation.objects
        .select_related("user", "assigned_to")
        .filter(user=user)
        .order_by("-last_message_at")
    )


def get_new_conversations() -> QuerySet[Conversation]:
    """
    Conversations waiting for support admin.
    """

    return (
        Conversation.objects
        .select_related("user")
        .filter(
            status=Conversation.Status.NEW,
            assigned_to__isnull=True,
        )
        .order_by("created_at")
    )


def get_assigned_conversations(
        support_admin: CustomUser,
) -> QuerySet[Conversation]:
    """
    Conversations assigned to support admin.
    """

    return (
        Conversation.objects
        .select_related("user")
        .filter(
            assigned_to=support_admin,
            status__in=[
                Conversation.Status.TAKEN,
                Conversation.Status.CLOSED
            ],
        )
        .order_by("-last_message_at")
    )


def count_today_conversations(user: CustomUser) -> int:
    """
    Count today's conversations.
    """

    from django.utils import timezone

    today = timezone.localdate()

    return (
        Conversation.objects
        .filter(
            user=user,
            created_at__date=today,
        )
        .count()
    )
