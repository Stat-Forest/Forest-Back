from rest_framework import serializers
from apps.reports.models import Report,ReportItem
from apps.reports.serializers import ReportItemSerializer, ReportItemPlantValueSerializer
from apps.utils.translation import get_lang_code, get_translated_field


class ReportListSerializer(serializers.ModelSerializer):
    period = serializers.CharField(source='statement.period')
    organization_name = serializers.SerializerMethodField()
    report_items = serializers.SerializerMethodField()
    statement__name = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            'id', 'organization', 'organization_name',
            'statement','statement__name'
            'deadline', 'period', 'status',
            'created_at', 'cancel_reason',
            'cancelled_at', 'sent_at', 'accepted_at',
            'report_items','sent_by','sent_by_org','sent_by_role'
        )

    def get_organization_name(self, obj):
        lang = get_lang_code(self.context)
        return get_translated_field(obj.organization, "name", lang)

    def get_report_items(self, obj):
        items = obj.report_items.all().select_related('statement_column', 'plant')
        result = {}
        lang = get_lang_code(self.context)

        for item in items:
            col_id = str(item.statement_column_id)
            if col_id not in result:
                result[col_id] = {
                    "statement_column_id": col_id,
                    "plant_values": []
                }

            plant_name = (
                get_translated_field(item.plant, "name", lang)
                if item.plant else None
            )

            result[col_id]["plant_values"].append({
                "plant_id": str(item.plant_id),
                "plant_name": plant_name,
                "value": item.value
            })

        return list(result.values())