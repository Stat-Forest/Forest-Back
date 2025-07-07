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
        lang = get_lang_code(self.context)
        translated = get_translated_field(obj, "name", lang)
        return translated or obj.name

    def get_parent_name(self, obj):
        if not obj.parent:
            return None
        lang = get_lang_code(self.context)
        return get_translated_field(obj.parent, "name", lang)

    def get_children(self, obj):
        if obj.parent is None:
            children = obj.children.all()
            serializer = PlantSerializer(
                children, many=True, context=self.context
            )
            return serializer.data
        return []

{
  "deadline": "4c18f7d2-7b6e-4fb7-a3d7-fcf1d3936905",
  "report_items": [
    {
      "statement_column": "277f6472-816b-497a-8dc0-74db000df282",
      "value": "67eefcc8-c9b8-45be-9456-481237d8afa5"
    },
    {
      "statement_column": "e01abc8c-d502-46f2-9ef0-7abfbf2ccb6c",
      "value": "10"
    },
    {
      "statement_column": "b121a091-b1d9-4f13-852b-fe77d8ae1e15",
      "value": "10"
    }
  ]
}