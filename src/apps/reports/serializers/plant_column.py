from rest_framework import serializers

from apps.base.serializers import CustomModelSerializer
from apps.reports.models import Plant
from apps.utils.translation import get_translated_field, get_lang_code


class PlantSerializer(CustomModelSerializer):
    name = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField(read_only=True)
    parent_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Plant
        fields = [
            "id",
            "name",
            "parent",
            "parent_name",
            "children"
        ]

    def get_name(self, obj):
        request = self.context["request"]
        lang = get_lang_code(request)
        translated = get_translated_field(obj, "name", lang)
        return translated or obj.name

    def get_parent_name(self, obj):
        return obj.parent.name if obj.parent else None

    def get_children(self, obj):
        if obj.parent is None:
            children = obj.children.all()
            serializer = PlantSerializer(
                children, many=True, context=self.context
            )
            return serializer.data
        return []