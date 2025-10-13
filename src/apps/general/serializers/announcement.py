from rest_framework import serializers

from apps.general.models import Announcement


class AnnouncementListSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    desc= serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = '__all__'

    def get_title(self, obj):
        lang = get_lang_code(self.context)
        translated = get_translated_field(obj, "title", lang)
        return translated or obj.title

    def get_desc(self, obj):
        lang = get_lang_code(self.context)
        translated = get_translated_field(obj, "desc", lang)
        return translated or obj.desc
