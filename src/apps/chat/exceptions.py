from rest_framework import status
from rest_framework.exceptions import APIException


class ChatException(APIException):
    """
    Base exception for chat module.

    DRF `APIException` dan meros oladi — shu sababli har bir xato
    o'zining to'g'ri HTTP statusi bilan qaytadi va view'larda qo'lda
    `try/except` yozish shart emas (`apps.base.handlers.custom_exception_handler`
    DRF'ning standart `exception_handler` ini chaqiradi).

    WebSocket consumer ham shu bazaviy sinfni ushlaydi.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Chat operation failed."
    default_code = "chat_error"


class ConversationNotFound(ChatException):
    """
    Conversation does not exist.
    """

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Conversation not found."
    default_code = "conversation_not_found"


class ConversationAlreadyAssigned(ChatException):
    """
    Conversation has already been assigned.
    """

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conversation already assigned."
    default_code = "conversation_already_assigned"


class ConversationAlreadyClosed(ChatException):
    """
    Conversation is already closed.
    """

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conversation already closed."
    default_code = "conversation_already_closed"


class ConversationAccessDenied(ChatException):
    """
    User has no access to this conversation.
    """

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You don't have access to this conversation."
    default_code = "conversation_access_denied"


class ConversationLimitExceeded(ChatException):
    """
    User has reached the daily conversation limit.
    """

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Daily conversation limit exceeded."
    default_code = "conversation_limit_exceeded"


class ConversationAlreadyExists(ChatException):
    """
    User already has an active conversation.
    """

    status_code = status.HTTP_409_CONFLICT
    default_detail = "You already have an active support conversation."
    default_code = "conversation_already_exists"


class SupportPermissionDenied(ChatException):
    """
    User is not allowed to perform support actions.
    """

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You are not allowed to perform this action."
    default_code = "support_permission_denied"


class MessageNotFound(ChatException):
    """
    Message does not exist.
    """

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Message not found."
    default_code = "message_not_found"


class ConversationNotAssigned(ChatException):
    """
    Conversation has not yet been assigned to any support administrator.
    """

    default_detail = "Conversation has not been assigned yet."
    default_code = "conversation_not_assigned"


class EmptyMessage(ChatException):
    """
    Empty message is not allowed.
    """

    default_detail = "Message cannot be empty."
    default_code = "empty_message"


class MessageTooLong(ChatException):
    """
    Message exceeds the allowed length.

    Model'dagi `MaxLengthValidator` `objects.create()` da ishlamaydi
    (validatorlar faqat `full_clean()` da yuriydi), shuning uchun
    uzunlik service darajasida tekshiriladi.
    """

    default_detail = "Message is too long."
    default_code = "message_too_long"
