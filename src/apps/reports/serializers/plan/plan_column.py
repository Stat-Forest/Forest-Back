from rest_framework import serializers
from apps.base.serializers import CustomModelSerializer
from apps.reports.models import StatementColumn


class PlanColumnSerializer(CustomModelSerializer):
    parent = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()

    class Meta:
        model = StatementColumn
        fields = [
            "id",
            "parent",
            "title",
            "ordering",
            "status_plan"
        ]

    def get_title(self, obj):
        lang = self.context.get("lang", "uz")
        return obj.title_ru if lang == "ru" else obj.title_uz

    def get_parent(self, obj):
        lang = self.context.get("lang", "uz")

        def build_parent_title(node):
            if node.parent is None:
                return node.title_ru if lang == "ru" else node.title_uz
            return f"{build_parent_title(node.parent)} - {(node.title_ru if lang == 'ru' else node.title_uz)}"

        return build_parent_title(obj)


