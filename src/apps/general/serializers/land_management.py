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
        lang = get_lang_code(self.context)
        return get_translated_field(obj, "name", lang) or obj.name

    def get_area(self, obj):
        # 3.050 -> 3.05, 881.000 -> 881
        return float(obj.area.normalize())
