from rest_framework import serializers
from apps.reports.models import Statement
from apps.utils.translation import get_translated_field, get_lang_code


class StatementChildSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    class Meta:
        model = Statement
        fields = ('id', 'name')

    def get_name(self, obj):
        lang = get_lang_code(self.context)
        translated = get_translated_field(obj, "name", lang)
        return translated or obj.name



class StatementSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = Statement
        fields = ('id', 'name', 'period', 'icon', 'parent', 'children')

    def get_name(self, obj):
        lang = get_lang_code(self.context)
        translated = get_translated_field(obj, "name", lang)
        return translated or obj.name

    def get_children(self, obj):
        children_qs = obj.children.filter(is_used=True)
        return StatementChildSerializer(
            children_qs,
            many=True,
            context=self.context
        ).data
