from rest_framework import serializers

from apps.base.serializers import CustomModelSerializer
from apps.chat.models import Message
from apps.users.models import CustomUser


class ChatUserSerializer(CustomModelSerializer):
    """
    Chatda ko'rsatiladigan yengil user ma'lumoti.

    `first_name`/`last_name` va `full_name` — uchalasi ham beriladi:
    ilgari REST birinchi ikkitasini, WebSocket esa `full_name` ni
    qaytarardi va bir xil xabar qayerdan kelganiga qarab turlicha
    ko'rinardi. Endi ikkala kanal ham shu yagona shakldan foydalanadi.
    """

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser

        fields = (
            "id",
            "first_name",
            "last_name",
            "full_name",
            "role",
        )

    def get_full_name(self, obj) -> str:
        return f"{obj.first_name} {obj.last_name}".strip()


class MessageSerializer(CustomModelSerializer):
    """
    Message serializer (REST va WebSocket uchun umumiy).
    """

    sender = ChatUserSerializer(read_only=True)

    class Meta:
        model = Message

        fields = (
            "id",
            "sender",
            "text",
            "is_read",
            "created_at",
        )
        read_only_fields = fields
