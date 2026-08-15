from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.chat.exceptions import (
    ConversationAlreadyAssigned,
    ConversationAlreadyClosed,
    ConversationAlreadyExists,
    ConversationAccessDenied,
    ConversationLimitExceeded,
    ConversationNotFound,
    SupportPermissionDenied,
)
from apps.chat.models import Conversation
from apps.chat.permissions import can_manage_support_chat, is_chat_supervisor
from apps.chat.selectors.conversation_selectors import (
    count_active_conversations,
    count_today_conversations,
    get_conversation_for_update,
    get_user_taken_conversation,
)
from apps.chat.websocket.events import (
    CONVERSATION_ASSIGNED,
    CONVERSATION_CLOSED,
    broadcast_conversation_event,
)
from apps.users.models import CustomUser

#: Bir kunda ochish mumkin bo'lgan chatlar soni.
MAX_CONVERSATIONS_PER_DAY = 2

#: Bir vaqtning o'zida yopilmagan (NEW + TAKEN) chatlar soni.
#: Kunlik limit bilan bir xil: shu kuni ochilgan ikkala chat ham javob
#: kutib turishi mumkin.
MAX_ACTIVE_CONVERSATIONS = 2


def _validate_can_create_conversation(
    *,
    user: CustomUser,
) -> None:
    """
    Validate whether user is allowed to create a new support conversation.

    Qoidalar:
        1. Admin qo'lidagi (TAKEN) chat bo'lsa — yangisi ochilmaydi.
           Foydalanuvchiga hozir xizmat ko'rsatilyapti.
        2. Yopilmagan chatlar soni limitdan oshmasin.
        3. Bugun ochilganlar soni limitdan oshmasin.

    MUHIM: hech kim olmagan NEW chat yangi chat ochishni TO'SMAYDI.
    Ilgari to'sardi va admin chatni olmasa foydalanuvchi butunlay
    qotib qolardi — kunlik 2 ta limitiga umuman yetib bora olmasdi.
    """

    if get_user_taken_conversation(user):
        raise ConversationAlreadyExists(
            "You already have a conversation being handled by support."
        )

    if count_active_conversations(user) >= MAX_ACTIVE_CONVERSATIONS:
        raise ConversationAlreadyExists(
            "You already have the maximum number of open support conversations."
        )

    if count_today_conversations(user) >= MAX_CONVERSATIONS_PER_DAY:
        raise ConversationLimitExceeded(
            "Daily conversation limit exceeded."
        )


def _validate_support_admin(
    *,
    user: CustomUser,
) -> None:
    """
    Ensure current user is support administrator.
    """

    if not can_manage_support_chat(user):
        raise SupportPermissionDenied(
            "You are not allowed to perform this action."
        )


def _validate_assigned_admin(
    *,
    conversation: Conversation,
    support_admin: CustomUser,
) -> None:
    """
    Only assigned support administrator
    may continue this conversation.

    Super admin (nazoratchi) bu cheklovdan ozod — tashlab ketilgan
    chatlarni majburan yopa olishi kerak.
    """

    if is_chat_supervisor(support_admin):
        return

    if conversation.assigned_to_id != support_admin.id:
        raise ConversationAccessDenied(
            "This conversation belongs to another support administrator."
        )


@transaction.atomic
def create_conversation(
    *,
    user: CustomUser,
) -> Conversation:
    """
    Create new support conversation.

    Initial status:

        NEW
    """

    # Foydalanuvchi qatorini qulflaymiz — shu orqali bitta userning
    # bir vaqtda kelgan ikkita so'rovi limit tekshiruvini aylanib
    # o'tolmaydi.
    (
        CustomUser.objects
        .select_for_update()
        .only("id")
        .get(pk=user.pk)
    )

    _validate_can_create_conversation(
        user=user,
    )

    try:
        # Ichki atomic bloki shart: IntegrityError tranzaksiyani buzadi va
        # nested blok bo'lmasa undan keyin hech qanday so'rov bajarib
        # bo'lmaydi (Django hujjatlarida ogohlantirilgan).
        with transaction.atomic():
            return Conversation.objects.create(
                user=user,
                status=Conversation.Status.NEW,
                created_by=user,
            )

    except IntegrityError:
        raise ConversationAlreadyExists(
            "You already have an active support conversation."
        )


@transaction.atomic
def assign_conversation(
    *,
    conversation_id: str,
    support_admin: CustomUser,
) -> Conversation:
    """
    Assign a NEW conversation to a support administrator.

    Only the first administrator who successfully takes the conversation
    becomes responsible for it until it is closed.
    """

    _validate_support_admin(user=support_admin)

    try:
        conversation = get_conversation_for_update(conversation_id)

    except Conversation.DoesNotExist:
        raise ConversationNotFound(
            "Conversation not found."
        )

    if conversation.status == Conversation.Status.CLOSED:
        raise ConversationAlreadyClosed(
            "Conversation already closed."
        )

    # Faqat NEW chat olinadi. `assigned_to` SET_NULL bo'lgani uchun admin
    # o'chirilsa TAKEN + assigned_to=NULL qator qolishi mumkin — uni qayta
    # olib, `taken_at` ni ustidan yozib yuborish noto'g'ri bo'lardi.
    if conversation.status != Conversation.Status.NEW:
        raise ConversationAlreadyAssigned(
            "Conversation already assigned."
        )

    if conversation.assigned_to_id is not None:
        raise ConversationAlreadyAssigned(
            "Conversation already assigned."
        )

    now = timezone.now()

    conversation.assigned_to = support_admin
    conversation.status = Conversation.Status.TAKEN
    conversation.taken_at = now
    conversation.updated_by = support_admin

    conversation.save(
        update_fields=[
            "assigned_to",
            "status",
            "taken_at",
            "updated_by",
            "updated_at",
        ]
    )

    transaction.on_commit(
        lambda: broadcast_conversation_event(
            conversation=conversation,
            event=CONVERSATION_ASSIGNED,
        )
    )

    return conversation


@transaction.atomic
def close_conversation(
    *,
    conversation_id: str,
    support_admin: CustomUser,
) -> Conversation:
    """
    Close a support conversation.

    Biriktirilgan support admin o'z chatini yopadi.
    Super admin esa tashlab ketilgan chatlarni — hali olinmagan NEW
    chatlarni ham — majburan yopa oladi.
    """

    _validate_support_admin(user=support_admin)

    try:
        conversation = get_conversation_for_update(conversation_id)

    except Conversation.DoesNotExist:
        raise ConversationNotFound(
            "Conversation not found."
        )

    if conversation.status == Conversation.Status.CLOSED:
        raise ConversationAlreadyClosed(
            "Conversation already closed."
        )

    # Hali olinmagan chatni faqat nazoratchi yopa oladi — oddiy admin
    # avval uni o'zlashtirib olishi kerak.
    if (
        conversation.status != Conversation.Status.TAKEN
        and not is_chat_supervisor(support_admin)
    ):
        raise ConversationAccessDenied(
            "Conversation has not been assigned yet."
        )

    _validate_assigned_admin(
        conversation=conversation,
        support_admin=support_admin,
    )

    return _close(conversation=conversation, closed_by=support_admin)


@transaction.atomic
def cancel_conversation(
    *,
    conversation_id: str,
    user: CustomUser,
) -> Conversation:
    """
    Foydalanuvchi o'zining hali OLINMAGAN chatini bekor qiladi.

    Admin allaqachon chatni olgan bo'lsa (TAKEN) — bekor qilib bo'lmaydi,
    uni faqat admin yopadi.

    Kunlik kvota QAYTARILMAYDI: aks holda "och — bekor qil — och" sikli
    kunlik limitni aylanib o'tish yo'liga aylanardi.
    """

    try:
        conversation = get_conversation_for_update(conversation_id)

    except Conversation.DoesNotExist:
        raise ConversationNotFound(
            "Conversation not found."
        )

    if conversation.user_id != user.id:
        raise ConversationAccessDenied(
            "You don't have access to this conversation."
        )

    if conversation.status == Conversation.Status.CLOSED:
        raise ConversationAlreadyClosed(
            "Conversation already closed."
        )

    if conversation.status != Conversation.Status.NEW:
        raise ConversationAccessDenied(
            "Conversation is already being handled by support."
        )

    return _close(conversation=conversation, closed_by=user)


def _close(
    *,
    conversation: Conversation,
    closed_by: CustomUser,
) -> Conversation:
    """
    Chatni CLOSED holatiga o'tkazish (umumiy qism).
    """

    conversation.status = Conversation.Status.CLOSED
    conversation.closed_at = timezone.now()
    conversation.updated_by = closed_by

    conversation.save(
        update_fields=[
            "status",
            "closed_at",
            "updated_by",
            "updated_at",
        ]
    )

    transaction.on_commit(
        lambda: broadcast_conversation_event(
            conversation=conversation,
            event=CONVERSATION_CLOSED,
        )
    )

    return conversation
