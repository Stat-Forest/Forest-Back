from rest_framework import serializers
from apps.general.models import Notification
from apps.utils.translation import get_translated_field


class NotificationListSerializer(serializers.ModelSerializer):
    text = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ["id", "text", "date", "created_at"]

    def get_text(self, obj):
        lang = self.context.get("lang", "uz")
        translated = get_translated_field(obj, "text", lang)
        return translated or obj.text
