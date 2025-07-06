from rest_framework import serializers
from apps.reports.models import StatementColumn
from apps.utils.translation import get_lang_code, get_translated_field


class StatementColumnTreeSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()

    children = serializers.SerializerMethodField()
    parent = serializers.PrimaryKeyRelatedField(read_only=True)
    statement = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = StatementColumn
        fields = [
            'id', 'statement', 'title',
            'ordering', 'parent', 'status_plan',
            'is_organization','children'
        ]

    def get_title(self, obj):
        lang = get_lang_code(self.context)
        translated = get_translated_field(obj, "title", lang)
        return translated

    def get_children(self, obj):
        if hasattr(obj, 'children_list'):
            return StatementColumnTreeSerializer(obj.children_list, many=True, context=self.context).data
        return []
