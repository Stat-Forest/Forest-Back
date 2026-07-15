from apps.chat.models import (
    Conversation,
    Message,
)
from apps.chat.websocket.chat_serializers import (
    ConversationSerializer,
    MessageSerializer,
)

ERROR_EVENT = "chat.error"


def build_message_created_event(
    message: Message,
) -> dict:
    """
    Broadcast newly created message.
    """

    return {
        "event": "message_created",
        "data": MessageSerializer(message).data,
    }


# def build_conversation_created_event(
#     conversation: Conversation,
# ) -> dict:
#     """
#     Broadcast newly created conversation.
#
#     Sent to all online support administrators.
#     """
#
#     return {
#         "event": "conversation_created",
#         "data": ConversationSerializer(conversation).data,
#     }


# def build_conversation_assigned_event(
#     conversation: Conversation,
# ) -> dict:
#     """
#     Broadcast conversation assignment.
#
#     Used to remove NEW conversation
#     from other support administrators.
#     """
#
#     return {
#         "event": "conversation_assigned",
#         "data": ConversationSerializer(conversation).data,
#     }
#
#
# def build_conversation_closed_event(
#     conversation: Conversation,
# ) -> dict:
#     """
#     Broadcast conversation closing.
#     """
#
#     return {
#         "event": "conversation_closed",
#         "data": ConversationSerializer(conversation).data,
#     }


# def build_messages_read_event(
#     conversation_id: str,
# ) -> dict:
#     """
#     Notify that messages were marked as read.
#     """
#
#     return {
#         "event": "messages_read",
#         "data": {
#             "conversation_id": str(conversation_id),
#         },
#     }


def build_error_event(
    code: str,
    message: str,
) -> dict:
    """
    Standard websocket error payload.
    """

    return {
        "event": "error",
        "data": {
            "code": code,
            "message": message
        }
    }


def conversation_group_name(
    conversation_id: str,
) -> str:
    """
    Return Channels group name for conversation.
    """

    return f"conversation_{conversation_id}"