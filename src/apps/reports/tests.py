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
        items = obj.report_items.all().select_related(
            'statement_column', 'plant', 'statement_column__parent'
        )
        lang = get_lang_code(self.context)

        # ✅ Faqat Ko‘chat yoki Nihol bo‘lsa plant_values struktura ishlaydi
        plant_items = items.filter(plant__isnull=False)
        is_kochat_or_nihol = any(
            item.statement_column.parent and
            item.statement_column.parent.title_uz in ["Ko‘chat-ilovasi", "Nihol-ilovasi"]
            for item in plant_items
        )

        if is_kochat_or_nihol:
            result = {}
            for item in plant_items:
                col_id = str(item.statement_column_id)
                if col_id not in result:
                    result[col_id] = {
                        "statement_column_id": col_id,
                        "statement_column_name": item.statement_column.title_uz,
                        "plant_values": [],
                    }

                result[col_id]["plant_values"].append({
                    "plant_id": str(item.plant_id),
                    "plant_name": get_translated_field(item.plant, "name", lang),
                    "value": item.value
                })

            return list(result.values())

        # ✅ Oddiy hisobotlar uchun
        from collections import OrderedDict
        org_groups = OrderedDict()
        current_group = []
        last_org_col_id = None

        for item in items.order_by('id'):
            if item.statement_column.is_organization:
                last_org_col_id = str(item.statement_column_id)
                current_group = []
                org_groups[last_org_col_id] = current_group

            if last_org_col_id is None:
                last_org_col_id = 'default'
                org_groups[last_org_col_id] = current_group

            current_group.append(item)

        result = []
        for group_items in org_groups.values():
            for item in group_items:
                col = item.statement_column
                result.append({
                    "statement_column_id": str(col.id),
                    "statement_column_name": col.title_uz,
                    "value": (
                        get_translated_field(obj.organization, "name", lang)
                        if col.is_organization else item.value
                    )
                })

        return result

    {
      "statement_column": "8047f96d-4d8b-44bd-a89e-28b4da00bec4",
      "value": "264ab991-b5b6-4014-8b6e-0df464bc5efe"
    },
    {
      "statement_column": "e4ba84b1-4718-4df5-8d88-ba2e088125b0",
      "value": "10"
    },
    {
      "statement_column": "d7ea11bf-8286-4292-bf81-4d50a64a0f94",
      "value": "10"
    },
    {
      "statement_column": "ba090034-d955-4d26-8d16-b42efda6dbef",
      "value": "10"
    }