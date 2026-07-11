from rest_framework import serializers

from apps.base.serializers import CustomModelSerializer
from apps.chat.models import Conversation, Message
from apps.users.models import CustomUser


# ==========================================================
# Incoming serializers
# ==========================================================


class SendMessageSerializer(serializers.Serializer):
    """
    Incoming websocket payload.

    {
        "action": "send_message",
        "text": "Hello"
    }
    """

    text = serializers.CharField(
        max_length=5000,
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


class AssignConversationSerializer(serializers.Serializer):
    """
    No payload required.

    {
        "action": "assign_conversation"
    }
    """

    pass


class CloseConversationSerializer(serializers.Serializer):
    """
    No payload required.

    {
        "action": "close_conversation"
    }
    """

    pass


# ==========================================================
# Outgoing serializers
# ==========================================================


class ChatUserSerializer(CustomModelSerializer):
    """
    Lightweight user representation.
    """

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser

        fields = (
            "id",
            "full_name",
            "role",
        )

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class MessageSerializer(CustomModelSerializer):
    """
    Message payload sent over websocket.
    """

    sender = ChatUserSerializer(
        read_only=True,
    )

    class Meta:
        model = Message

        fields = (
            "id",
            "sender",
            "text",
            "is_read",
            "created_at",
        )


class ConversationSerializer(CustomModelSerializer):
    """
    Conversation payload sent over websocket.
    """

    user = ChatUserSerializer(
        read_only=True,
    )

    assigned_to = ChatUserSerializer(
        read_only=True,
    )

    class Meta:
        model = Conversation

        fields = (
            "id",
            "status",
            "user",
            "assigned_to",
            "taken_at",
            "closed_at",
            "last_message_at",
            "created_at",
        )