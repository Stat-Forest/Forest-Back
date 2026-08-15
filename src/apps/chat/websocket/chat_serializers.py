from rest_framework import serializers

from apps.chat.models.chat import MAX_MESSAGE_LENGTH
from apps.chat.serializers.conversation_serializers import (
    ConversationDetailSerializer as ConversationSerializer,
)
from apps.chat.serializers.message_serializers import (
    ChatUserSerializer,
    MessageSerializer,
)

# Chiquvchi payloadlar REST bilan bir xil serializerlardan quriladi —
# ilgari bu yerda alohida nusxalari bor edi va bitta xabar tarixdan
# kelganda boshqa, jonli kelganda boshqa shaklda ko'rinardi.
__all__ = [
    "SendMessageSerializer",
    "MessageSerializer",
    "ConversationSerializer",
    "ChatUserSerializer",
]


class SendMessageSerializer(serializers.Serializer):
    """
    Incoming websocket payload.

    {
        "text": "Hello"
    }
    """

    text = serializers.CharField(
        max_length=MAX_MESSAGE_LENGTH,
        trim_whitespace=True,
    )

    def validate_text(self, value: str) -> str:
        """
        Prevent sending empty messages.
        """

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Message cannot be empty."
            )

        return value
