from rest_framework import serializers

from apps.base.serializers import CustomModelSerializer
from apps.chat.models import Conversation
from apps.users.models import CustomUser


def _serialize_user(user: CustomUser | None) -> dict | None:
    """
    Shared lightweight user representation used across
    conversation serializers.
    """
    if user is None:
        return None

    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "role": user.role,
    }


class ConversationCreateSerializer(serializers.Serializer):
    """
    Empty serializer.

    User is taken from request.user.
    """
    pass


class ConversationListSerializer(CustomModelSerializer):
    """
    Conversation list serializer.
    """

    user = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation

        fields = (
            "id",
            "user",
            "status",
            "assigned_to",
            "last_message_at",
            "created_at",
            "unread_count",
        )

    def get_user(self, obj):
        return _serialize_user(obj.user)

    def get_assigned_to(self, obj):
        return _serialize_user(obj.assigned_to)

    def get_unread_count(self, obj):
        user = self.context["request"].user

        return (
            obj.messages
            .filter(is_read=False)
            .exclude(sender=user)
            .count()
        )


class ConversationDetailSerializer(CustomModelSerializer):
    """
    Conversation detail serializer.
    """

    user = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()

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

    def get_user(self, obj):
        return _serialize_user(obj.user)

    def get_assigned_to(self, obj):
        return _serialize_user(obj.assigned_to)