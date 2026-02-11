from rest_framework import serializers
from apps.reports.models import Statement
from apps.utils.translation import get_translated_field, get_lang_code


class StatementChildSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Statement
        fields = ('id', 'name')

    def get_name(self, obj):
        lang = self.context.get('lang', 'uz')
        translated = get_translated_field(obj, "name", lang)
        return translated or obj.name


class StatementSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = Statement
        fields = ('id', 'name', 'period', 'icon', 'parent', 'children')

    def get_name(self, obj):
        lang = self.context.get('lang', 'uz')
        translated = get_translated_field(obj, "name", lang)
        return translated or obj.name

    def get_children(self, obj):
        lang = self.context.get('lang', 'uz')

        # Prefetch qilingan children'dan foydalanish (queryset optimization)
        children_qs = obj.children.all() if hasattr(obj, '_prefetched_objects_cache') else obj.children.filter(
            is_used=True)

        children_data = []
        for child in children_qs:
            translated_name = get_translated_field(child, "name", lang) or child.name
            children_data.append({
                'id': child.id,
                'name': translated_name
            })

        # Alfabetga qarab saralash (case-insensitive)
        children_data.sort(key=lambda x: x['name'].lower())
        return children_data