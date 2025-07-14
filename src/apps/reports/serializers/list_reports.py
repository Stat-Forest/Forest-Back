from rest_framework import serializers
from apps.reports.models import Report,ReportItem
from apps.reports.serializers import ReportItemSerializer, ReportItemPlantValueSerializer
from apps.utils.translation import get_lang_code, get_translated_field


class ReportListSerializer(serializers.ModelSerializer):
    period = serializers.CharField(source='statement.period')
    organization_name = serializers.SerializerMethodField()
    report_items = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            'id', 'organization', 'organization_name',
            'statement',
            'deadline', 'period', 'status',
            'created_at', 'cancel_reason',
            'cancelled_at', 'sent_at', 'accepted_at',
            'report_items'
        )

    def get_organization_name(self, obj):
        lang = get_lang_code(self.context)
        return get_translated_field(obj.organization, "name", lang)

    def get_report_items(self, obj):
        items = obj.report_items.all().select_related('statement_column', 'plant')
        lang = get_lang_code(self.context)

        # 🌿 1. Ko‘chat yoki Nihol bo‘lsa (ya'ni plant bor)
        has_plants = items.filter(plant__isnull=False).exists()
        has_organization_column = items.filter(plant__isnull=True).exists()

        if has_plants:
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
                    result[col_id]["value"] = get_translated_field(obj.organization, "name", lang)

            return list(result.values())

        # 📄 2. Oddiy hisobotlar (plant yo‘q, value ham yo‘q, odatiy forma)
        if not has_organization_column:
            return [
                ReportItemSerializer(item, context=self.context).data
                for item in items
            ]

        # 🏢 3. Faqat organization bo‘yicha bo‘lsa (value — tashkilot nomi bo‘lishi kerak)
        result = []
        for item in items:
            result.append({
                "statement_column_id": str(item.statement_column_id),
                "statement_column_name": item.statement_column.title_uz,
                "value": get_translated_field(obj.organization, "name", lang)
            })

        return result