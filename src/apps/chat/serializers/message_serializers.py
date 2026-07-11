from rest_framework import serializers

from apps.base.serializers import CustomModelSerializer
from apps.chat.models import Message


class MessageSerializer(CustomModelSerializer):
    """
    Message serializer.
    """

    sender = serializers.SerializerMethodField()

    class Meta:
        model = Message

        fields = (
            "id",
            "sender",
            "text",
            "is_read",
            "created_at",
        )

    def get_sender(self, obj):
        return {
            "id": obj.sender.id,
            "first_name": obj.sender.first_name,
            "last_name": obj.sender.last_name,
            "role": obj.sender.role,
        }