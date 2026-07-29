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



class OrganizationMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "name")


class RegionOrganizationsSerializer(serializers.Serializer):
    region = serializers.CharField()
    count = serializers.IntegerField()
    display = serializers.CharField()
    organizations = OrganizationMiniSerializer(many=True)


class RepublicSerializer(serializers.Serializer):
    label = serializers.CharField()
    count = serializers.IntegerField()
    display = serializers.CharField()


class OrganizationsByRegionResponseSerializer(serializers.Serializer):
    republic = RepublicSerializer()
    regions = RegionOrganizationsSerializer(many=True)