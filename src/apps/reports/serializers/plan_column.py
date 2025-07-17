from rest_framework import serializers
from apps.base.serializers import CustomModelSerializer
from apps.reports.models import StatementColumn


class PlanColumnSerializer(CustomModelSerializer):
    parent = serializers.StringRelatedField()
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
        if lang == "ru":
            return obj.title_ru
        return obj.title_uz
