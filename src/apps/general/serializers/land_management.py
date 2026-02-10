from rest_framework import serializers
from apps.general.models import LandManagement
from apps.utils.translation import get_translated_field, get_lang_code


class LandManagementItemSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    area = serializers.SerializerMethodField()

    class Meta:
        model = LandManagement
        fields = ('name', 'area')

    def get_name(self, obj):
        # Agar context'da lang bo'lsa, uni ishlatamiz
        lang = self.context.get("lang") or get_lang_code(self.context)
        return get_translated_field(obj, "name", lang) or obj.name

    def get_area(self, obj):
        return float(obj.area.normalize())

