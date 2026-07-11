class ChatException(Exception):
    """
    Base exception for chat module.
    """


class ConversationNotFound(ChatException):
    """
    Conversation does not exist.
    """


class ConversationAlreadyAssigned(ChatException):
    """
    Conversation has already been assigned.
    """


class ConversationAlreadyClosed(ChatException):
    """
    Conversation is already closed.
    """


class ConversationAccessDenied(ChatException):
    """
    User has no access to this conversation.
    """


class ConversationLimitExceeded(ChatException):
    """
    User has reached the daily conversation limit.
    """


class ConversationAlreadyExists(ChatException):
    """
    User already has an active conversation.
    """


class SupportPermissionDenied(ChatException):
    """
    User is not allowed to perform support actions.
    """

class MessageNotFound(ChatException):
    """
    Message does not exist.
    """


class ConversationNotAssigned(ChatException):
    """
    Conversation has not yet been assigned to any support administrator.
    """


class EmptyMessage(ChatException):
    """
    Empty message is not allowed.
    """