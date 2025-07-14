from rest_framework import serializers
from apps.reports.models import Report,ReportItem
from apps.reports.serializers import ReportItemSerializer, ReportItemPlantValueSerializer
from apps.utils.translation import get_lang_code, get_translated_field


from rest_framework import serializers
from apps.reports.models import Report
from apps.utils.translation import get_lang_code, get_translated_field


class ReportListSerializer(serializers.ModelSerializer):
    period = serializers.CharField(source='statement.period')
    organization_name = serializers.SerializerMethodField()
    report_items = serializers.SerializerMethodField()
    statement_name = serializers.SerializerMethodField()
    sent_by_full_name = serializers.SerializerMethodField()
    sent_by_org_name = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            'id', 'organization', 'organization_name',
            'statement', 'statement_name',
            'deadline', 'period', 'status',
            'created_at', 'cancel_reason',
            'cancelled_at', 'sent_at', 'accepted_at',
            'report_items',
            'sent_by_full_name', 'sent_by_org_name', 'sent_by_role',
        )

    def get_organization_name(self, obj):
        lang = get_lang_code(self.context)
        return get_translated_field(obj.organization, "name", lang)

    def get_statement_name(self, obj):
        lang = get_lang_code(self.context)
        return get_translated_field(obj.statement, "name", lang)

    def get_sent_by_full_name(self, obj):
        if obj.sent_by:
            return obj.sent_by.full_name
        return None

    def get_sent_by_org_name(self, obj):
        lang = get_lang_code(self.context)
        if obj.sent_by_org:
            return get_translated_field(obj.sent_by_org, "name", lang)
        return None

    def get_report_items(self, obj):
        items = obj.report_items.all().select_related('statement_column', 'plant')
        lang = get_lang_code(self.context)

        # 🌿 1. Plant-based bo‘lsa (Ko‘chat/Nihol ilovalari)
        if items.filter(plant__isnull=False).exists():
            result = {}

            for item in items:
                col_id = str(item.statement_column_id)
                if col_id not in result:
                    result[col_id] = {
                        "statement_column_id": col_id,
                        "statement_column_name": item.statement_column.title_uz,
                        "plant_values": [] if item.plant_id else None,
                        "value": None
                    }

                if item.plant_id:
                    result[col_id]["plant_values"].append({
                        "plant_id": str(item.plant_id),
                        "plant_name": get_translated_field(item.plant, "name", lang),
                        "value": item.value
                    })
                else:
                    if item.statement_column.is_organization:
                        result[col_id]["value"] = get_translated_field(obj.organization, "name", lang)
                    else:
                        result[col_id]["value"] = item.value

            return list(result.values())

        # 📄 2. Oddiy hisobotlar (plant yo‘q)
        org_items = []
        other_items = []

        for item in items:
            record = {
                "statement_column_id": str(item.statement_column_id),
                "value": (
                    get_translated_field(obj.organization, "name", lang)
                    if item.statement_column.is_organization
                    else item.value
                )
            }

            if item.statement_column.is_organization:
                org_items.append(record)
            else:
                other_items.append(record)

        # ⬆️ Organization item always first
        return org_items + other_items