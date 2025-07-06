from rest_framework import serializers
from apps.reports.models import Report,ReportItem
from apps.reports.serializers import ReportItemSerializer, ReportItemPlantValueSerializer
from apps.utils.translation import get_lang_code, get_translated_field


class ReportListSerializer(serializers.ModelSerializer):
    period = serializers.CharField(source='statement.period')
    organization_name = serializers.SerializerMethodField()
    statement_name = serializers.SerializerMethodField()
    report_items = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            'id', 'organization', 'organization_name',
            'statement', 'statement_name',
            'deadline', 'period', 'status',
            'created_at', 'cancel_reason',
            'cancelled_at', 'sent_at', 'accepted_at',
            'report_items'
        )

    def get_organization_name(self, obj):
        lang = get_lang_code(self.context)
        return get_translated_field(obj.organization, "name", lang)

    def get_statement_name(self, obj):
        lang = get_lang_code(self.context)
        return get_translated_field(obj.statement, "name", lang)

    def get_report_items(self, obj):
        items = obj.report_items.all()
        result = []

        for item in items:
            if item.plant_id:
                ser = ReportItemPlantValueSerializer(item, context=self.context)
            else:
                ser = ReportItemSerializer(item, context=self.context)
            result.append(ser.data)

        return result