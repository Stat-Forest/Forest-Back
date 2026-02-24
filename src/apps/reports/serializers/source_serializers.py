from rest_framework import serializers

from apps.reports.models import Report
from apps.base.serializers import CustomModelSerializer
from apps.utils.translation import get_lang_code, get_translated_field


class SourceReportSerializer(CustomModelSerializer):
    organization_name = serializers.SerializerMethodField()
    statement_name = serializers.SerializerMethodField()
    submit_at = serializers.CharField(source="deadline.submit_at")

    class Meta:
        model = Report
        fields = [
            "id",
            "organization",
            "organization_name",
            "statement",
            "statement_name",
            "deadline",
            "submit_at",
            "status",
            "created_at",
        ]

    def get_organization_name(self, obj):
        lang = get_lang_code(self.context)
        return get_translated_field(obj.organization, "name", lang)

    def get_statement_name(self, obj):
        lang = get_lang_code(self.context)
        return get_translated_field(obj.statement, "name", lang)