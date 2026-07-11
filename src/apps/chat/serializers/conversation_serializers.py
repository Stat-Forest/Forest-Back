from rest_framework import serializers

from apps.base.serializers import CustomModelSerializer
from apps.chat.models import Conversation
from apps.users.models import CustomUser


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

    assigned_to = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation

        fields = (
            "id",
            "status",
            "assigned_to",
            "last_message_at",
            "created_at",
            "unread_count",
        )

    def get_assigned_to(self, obj):
        if obj.assigned_to is None:
            return None

        return {
            "id": obj.assigned_to.id,
            "full_name": (
                f"{obj.assigned_to.first_name} "
                f"{obj.assigned_to.last_name}"
            ),
        }

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

    def _user_data(
        self,
        user: CustomUser | None,
    ):
        if user is None:
            return None

        return {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role": user.role,
        }

    def get_user(self, obj):
        return self._user_data(obj.user)

    def get_assigned_to(self, obj):
        return self._user_data(obj.assigned_to)