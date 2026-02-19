# ==============================
# serializers.py
# ==============================
from rest_framework import serializers
from apps.general.models import Notification
from apps.utils.translation import get_translated_field


class NotificationListSerializer(serializers.ModelSerializer):
    """
    Serializer for Notification.
    Returns translated text based on 'lang' context.
    """

    text = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ["id", "text", "date", "created_at"]

    def get_text(self, obj):
        """
        Return translated text based on requested language.
        Defaults to Uzbek ("uz") if not specified or translation missing.
        """
        lang = self.context.get("lang", "uz")
        translated = get_translated_field(obj, "text", lang)
        return translated or obj.text
