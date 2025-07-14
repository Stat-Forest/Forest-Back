from rest_framework import serializers

from apps.general.models import Organization
from apps.utils.translation import get_lang_code, get_translated_field


class OrganizationListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ['id', 'name', 'stir','region']

    def get_name(self, obj):
        lang = get_lang_code(self.context)
        translated = get_translated_field(obj, "name", lang)
        return translated or obj.name