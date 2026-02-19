# ==============================
# serializers.py
# ==============================
from rest_framework import serializers
from apps.general.models import LandManagement
from apps.utils.translation import get_translated_field, get_lang_code


class LandManagementItemSerializer(serializers.ModelSerializer):
    """
    Serializer for LandManagement items.
    Handles multilingual 'name' translation.
    """

    name = serializers.SerializerMethodField()

    class Meta:
        model = LandManagement
        fields = ('name', 'area')

    def get_name(self, obj):
        """
        Returns translated name based on 'lang' context.
        Falls back to original 'name' if translation is not available.
        """
        lang = self.context.get("lang") or get_lang_code(self.context)
        return get_translated_field(obj, "name", lang) or obj.name
