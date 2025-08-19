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

        organization_id = (
            "general" if report.is_general else str(report.organization.id)
        )
        organization_name = (
            "Barcha tashkilotlar bo‘yicha umumiy"
            if report.is_general
            else get_translated_field(report.organization, "name", lang)
        )

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
                    # Agar organization ustuni bo‘lsa, tashkilot nomini value sifatida chiqaramiz
                    if column.is_organization:
                        val = (
                            "Jami" if report.is_general
                            else get_translated_field(report.organization, "name", lang)
                        )
                        inner_values.append({"id": str(inner.id), "value": val})
                    else:
                        inner_values.append({"id": str(inner.id), "value": inner.value})

                statement_columns.append({
                    "statement_column_id": str(column.id),
                    "statement_column_name": get_translated_field(column, "title", lang),
                    "inners": inner_values
                })

        return [{
            "organization_id": organization_id,
            "organization_name": organization_name,
            "statement_columns": statement_columns
        }]

    # def get_report_items(self, report):
    #     lang = get_lang_code(self.context)
    #     # ❗️ Bunda inner so‘rov ketmaydi, chunki oldindan prefetch bo‘lgan
    #     items = report.report_items.all()
    #
    #     if report.is_general:
    #         organization_id = "general"
    #         organization_name = "Barcha tashkilotlar bo‘yicha umumiy"
    #
    #         org_qs = Report.objects.filter(
    #             statement=report.statement,
    #             deadline=report.deadline,
    #             is_general=False
    #         ).values("organization_id", "organization__name").distinct()
    #
    #         org_inners = [
    #             {"id": str(o["organization_id"]), "value": o["organization__name"] or ""}
    #             for o in org_qs
    #         ]
    #
    #         org_column = StatementColumn.objects.filter(
    #             statement=report.statement,
    #             is_organization=True
    #         ).first()
    #
    #         org_column_json = {
    #             "statement_column_id": str(org_column.id),
    #             "statement_column_name": get_translated_field(org_column, "title", lang),
    #             "inners": org_inners
    #         }
    #
    #         other_columns = []
    #         for item in items:
    #             if item.statement_column.is_organization:
    #                 continue
    #             other_columns.append({
    #                 "statement_column_id": str(item.statement_column.id),
    #                 "statement_column_name": get_translated_field(item.statement_column, "title", lang),
    #                 # ❗️ Bu yerda endi query bo‘lmaydi
    #                 "inners": [
    #                     {"id": str(inner.id), "value": inner.value}
    #                     for inner in item.inners.all()
    #                 ]
    #             })
    #
    #         return [{
    #             "organization_id": organization_id,
    #             "organization_name": organization_name,
    #             "statement_columns": [org_column_json] + other_columns
    #         }]
    #     else:
    #         return [{
    #             "organization_id": str(report.organization.id),
    #             "organization_name": report.organization.name,
    #             "statement_columns": [
    #                 {
    #                     "statement_column_id": str(item.statement_column.id),
    #                     "statement_column_name": get_translated_field(item.statement_column, "title", lang),
    #                     # ❗️ Bu yerda ham query bo‘lmaydi
    #                     "inners": [
    #                         {"id": str(inner.id), "value": inner.value}
    #                         for inner in item.inners.all()
    #                     ]
    #                 }
    #                 for item in items
    #             ]
    #         }]


