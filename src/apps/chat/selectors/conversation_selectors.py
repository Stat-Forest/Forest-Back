from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from apps.chat.models.chat import CONVERSATION_ACTIVITY, Conversation
from apps.chat.permissions import can_manage_support_chat
from apps.users.models import CustomUser

#: Chatlar ro'yxatining standart tartibi.
#: `-last_message_at` yolg'iz o'zi Postgres'da NULL larni birinchi qo'yadi —
#: shuning uchun Coalesce ishlatiladi (`CONVERSATION_ACTIVITY`), oxirida esa
#: pagination barqaror bo'lishi uchun tie-breaker turadi.
CONVERSATION_ORDERING = (CONVERSATION_ACTIVITY.desc(), "-created_at")


def unread_count_annotation(user: CustomUser) -> Count:
    """
    Foydalanuvchi uchun o'qilmagan xabarlar soni.

    Bu annotate serializer ichidagi har bir qator uchun alohida
    `COUNT` so'rovini (N+1) almashtiradi.
    """

    return Count(
        "messages",
        filter=Q(messages__is_read=False) & ~Q(messages__sender_id=user.pk),
    )


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
        - Any support administrator (faqat O'QISH uchun — navbatdagi
          NEW chatni ochib savolni ko'rish imkoniyati)

    DIQQAT: bu O'QISH ruxsati. Yozish huquqi alohida —
    `message_services._validate_sender_access` ni qarang.
    """

    queryset = (
        Conversation.objects
        .select_related(
            "user",
            "assigned_to",
        )
        .filter(
            id=conversation_id,
        )
    )

    if not can_manage_support_chat(user):
        queryset = queryset.filter(
            Q(user=user)
            |
            Q(assigned_to=user)
        )

    return queryset.first()


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
    Return user's active conversation (NEW yoki TAKEN).
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


def get_user_taken_conversation(user: CustomUser) -> Conversation | None:
    """
    Foydalanuvchining admin qo'lidagi (TAKEN) chati.

    Aynan shu holat yangi chat ochishni to'sadi — NEW chat esa hech kimni
    band qilmagani uchun to'smaydi.
    """

    return (
        Conversation.objects
        .select_related("assigned_to")
        .filter(
            user=user,
            status=Conversation.Status.TAKEN,
        )
        .first()
    )


def count_active_conversations(user: CustomUser) -> int:
    """
    Foydalanuvchining yopilmagan (NEW + TAKEN) chatlari soni.
    """

    return (
        Conversation.objects
        .filter(
            user=user,
            status__in=[
                Conversation.Status.NEW,
                Conversation.Status.TAKEN,
            ],
        )
        .count()
    )


def get_user_conversations(user: CustomUser) -> QuerySet[Conversation]:
    """
    Return all conversations of user.
    """

    return (
        Conversation.objects
        .select_related("user", "assigned_to")
        .filter(user=user)
        .annotate(unread_count=unread_count_annotation(user))
        .order_by(*CONVERSATION_ORDERING)
    )


def get_new_conversations(viewer: CustomUser) -> QuerySet[Conversation]:
    """
    Conversations waiting for support admin.
    """

    return (
        Conversation.objects
        .select_related("user", "assigned_to")
        .filter(
            status=Conversation.Status.NEW,
            assigned_to__isnull=True,
        )
        .annotate(unread_count=unread_count_annotation(viewer))
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
        .select_related("user", "assigned_to")
        .filter(
            assigned_to=support_admin,
            status__in=[
                Conversation.Status.TAKEN,
                Conversation.Status.CLOSED
            ],
        )
        .annotate(unread_count=unread_count_annotation(support_admin))
        .order_by(*CONVERSATION_ORDERING)
    )


def count_today_conversations(user: CustomUser) -> int:
    """
    Count today's conversations.

    `timezone.localdate()` va `created_at__date` ikkalasi ham joriy
    timezone (Asia/Tashkent) da hisoblanadi, shuning uchun kun chegarasi
    Python va SQL tomonda bir xil bo'ladi.
    """

    today = timezone.localdate()

    return (
        Conversation.objects
        .filter(
            user=user,
            created_at__date=today,
        )
        .count()
    )
