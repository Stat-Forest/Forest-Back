import re

from rest_framework import serializers
from apps.reports.models import Report, StatementColumn
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

    def get_report_items(self, report):
        lang = get_lang_code(self.context)

        items = list(
            report.report_items.select_related("statement_column").prefetch_related("inners").all()
        )

        def ordering_key(ordering: str):
            if not ordering:
                return []
            return [int(part) if part.isdigit() else part for part in re.split(r'(\d+)', ordering)]

        # Natural sort: Har bir columnni ordering bo‘yicha tartiblaymiz
        items.sort(key=lambda i: ordering_key(i.statement_column.ordering or ""))

        # Ilovalar bo‘yicha grouping qilish uchun top-level ilovani aniqlaymiz: 1., 2., 3. kabi
        def get_top_level_ordering(ordering: str) -> str:
            return ordering.split(".")[0] if ordering else "0"

        # ✅ ORGANIZATION NAME – FAQAT SHU QISM O‘ZGARGAN
        if report.is_general:
            organization_id = "general"
            organization_name = "Viloyat darajasidagi Jami"
        elif getattr(report, "is_individual_general", False):  # Agar flag mavjud bo‘lsa
            organization_id = "individual"
            organization_name = f"{get_translated_field(report.organization, 'name', lang)} – Tashkilot Jami"
        else:
            organization_id = str(report.organization.id)
            organization_name = get_translated_field(report.organization, "name", lang)

        # Top-level ilovalar bo‘yicha guruhlash (1-ilova, 2-ilova, 3-ilova...)
        grouped_by_ilova = {}
        for item in items:
            top_level = get_top_level_ordering(item.statement_column.ordering)
            grouped_by_ilova.setdefault(top_level, []).append(item)

        statement_columns = []

        # Ilovalar ketma-ketligi bo‘yicha aylanamiz (1, 2, 3 ...)
        for ilova_ordering in sorted(grouped_by_ilova.keys(), key=lambda x: int(x)):
            for item in grouped_by_ilova[ilova_ordering]:
                column = item.statement_column
                inner_values = []

                for inner in item.inners.all():
                    if column.is_organization:
                        val = inner.value  # default
                        column_title = getattr(column, f"title_{lang}", "")

                        if column_title.lower() in ["tashkilot nomi", "название организации"]:
                            if report.is_individual_general or report.is_general:
                                val = get_translated_field(report.organization, "name", lang)
                                suffix = " – Tashkilot Jami" if report.is_individual_general else " – Viloyat Jami"
                                val = f"{val}{suffix}"

                        inner_values.append({"id": str(inner.id), "value": val})
                    else:
                        inner_values.append({"id": str(inner.id), "value": inner.value})

                statement_columns.append({
                    "statement_column_id": str(column.id),
                    "statement_column_name": get_translated_field(column, "title", lang),
                    "inners": inner_values
                })

        data = [{
            "organization_id": organization_id,
            "organization_name": organization_name,
            "statement_columns": statement_columns
        }]

        data.sort(key=lambda item: (
            0 if item["organization_id"] not in ["individual", "general"]
            else 1 if item["organization_id"] == "individual"
            else 2
        ))

        return data
