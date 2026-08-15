from rest_framework import serializers

from apps.base.serializers import CustomModelSerializer
from apps.chat.models import Conversation
from apps.chat.serializers.message_serializers import ChatUserSerializer


class ConversationUserSerializer(ChatUserSerializer):
    """
    Chat egasi / admin ma'lumoti — email bilan.

    Email faqat chatga kirish huquqi bor tomonlarga ko'rinadi
    (support endpointlari `IsSupportAdmin` bilan yopilgan).
    """

    class Meta(ChatUserSerializer.Meta):
        fields = ChatUserSerializer.Meta.fields + ("email",)


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

    user = ConversationUserSerializer(read_only=True)
    assigned_to = ConversationUserSerializer(read_only=True)
    unread_count = serializers.IntegerField(read_only=True)

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
        read_only_fields = fields


class ConversationDetailSerializer(CustomModelSerializer):
    """
    Conversation detail serializer.
    """

    user = ConversationUserSerializer(read_only=True)
    assigned_to = ConversationUserSerializer(read_only=True)

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
        read_only_fields = fields
