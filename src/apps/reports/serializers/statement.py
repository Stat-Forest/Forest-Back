# serializers.py
from rest_framework import serializers
from apps.reports.models import Statement
from apps.utils.translation import get_translated_field, get_lang_code


class StatementChildSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    class Meta:
        model = Statement
        fields = ('id', 'name')

    def get_name(self, obj):
        request = self.context.get("request")
        lang = get_lang_code(request)
        translated = get_translated_field(obj, "name", lang)
        return translated or obj.name

class StatementSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    children = StatementChildSerializer(many=True, read_only=True)

    class Meta:
        model = Statement
        fields = ('id', 'name', 'period','icon', 'parent', 'children')

    def get_name(self, obj):
        request = self.context.get("request")
        lang = get_lang_code(request)
        translated = get_translated_field(obj, "name", lang)
        return translated or obj.name