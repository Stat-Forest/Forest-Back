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
from apps.chat.selectors.conversation_selectors import (
    count_today_conversations,
    get_conversation_for_update,
    get_user_active_conversation,
)
from apps.users.models import CustomUser


def _validate_can_create_conversation(
    *,
    user: CustomUser,
) -> None:
    """
    Validate whether user is allowed to create a new support conversation.
    """

    if get_user_active_conversation(user):
        raise ConversationAlreadyExists(
            "You already have an active support conversation."
        )

    if count_today_conversations(user) >= 2:
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

    if not user.has_perm("chat.manage_support_chat"):
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
    """

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
        ]
    )

    return conversation


@transaction.atomic
def close_conversation(
    *,
    conversation_id: str,
    support_admin: CustomUser,
) -> Conversation:
    """
    Close an assigned support conversation.

    Only the assigned support administrator
    can close the conversation.
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

    if conversation.status != Conversation.Status.TAKEN:
        raise ConversationAccessDenied(
            "Conversation has not been assigned yet."
        )

    _validate_assigned_admin(
        conversation=conversation,
        support_admin=support_admin,
    )

    now = timezone.now()

    conversation.status = Conversation.Status.CLOSED
    conversation.closed_at = now
    conversation.updated_by = support_admin

    conversation.save(
        update_fields=[
            "status",
            "closed_at",
            "updated_by",
            "updated_at",
        ]
    )

    return conversation