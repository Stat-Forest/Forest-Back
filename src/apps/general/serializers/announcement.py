from rest_framework import serializers
from apps.general.models import Announcement
from apps.utils.translation import get_translated_field


class AnnouncementListSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    desc = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            "id",
            "title",
            "desc",
            "image",
            "lnk",
            "ordering",
            "created_at",
        ]

    def get_title(self, obj):
        lang = self.context.get("lang", "uz")
        translated = get_translated_field(obj, "title", lang)
        return translated if translated else obj.title

    def get_desc(self, obj):
        lang = self.context.get("lang", "uz")
        translated = get_translated_field(obj, "desc", lang)
        return translated if translated else obj.desc
