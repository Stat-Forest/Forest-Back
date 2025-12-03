import re
from collections import defaultdict
from rest_framework import serializers
from apps.utils.services import RegionChoices
from apps.reports.models import ReportItemInner, Report
from apps.utils.translation import get_lang_code, get_translated_field


class GeneralReportItemInnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportItemInner
        fields = ["id", "value"]


class GeneralReportStatementColumnSerializer(serializers.Serializer):
    statement_column_id = serializers.UUIDField()
    statement_column_name = serializers.CharField()
    inners = GeneralReportItemInnerSerializer(many=True)


class GeneralReportItemSerializer(serializers.Serializer):
    organization_id = serializers.CharField()
    organization_name = serializers.CharField()
    statement_columns = GeneralReportStatementColumnSerializer(many=True)


class RegionalGeneralReportSerializer(serializers.ModelSerializer):
    report_items = serializers.SerializerMethodField()
    children_reports = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
            "organization_name",
            "report_items",
            "children_reports",
        ]

    def get_organization_name(self, report):
        region_label = dict(RegionChoices.choices).get(report.region, "Nomaʼlum")
        lang = get_lang_code(self.context)
        return f"{region_label} – {'Вилоятный итог' if lang == 'ru' else 'Viloyat Jami'}"

    def _ordering_key(self, ordering):
        if not ordering:
            return []
        return [int(part) if part.isdigit() else part for part in re.split(r'(\d+)', ordering)]

    def _get_top_level_ordering(self, ordering):
        return ordering.split(".")[0] if ordering else "0"

    def _is_org_name_column(self, column, lang):
        title = getattr(column, f"title_{lang}", "").strip().lower()
        return column.is_organization and title in ["tashkilot nomi", "название организации", "наименование организации"]

    def _get_grouped_statement_columns(self, items, lang, org_name):
        grouped_by_ilova = defaultdict(list)
        for item in items:
            if item.statement_column:
                top_level = self._get_top_level_ordering(item.statement_column.ordering or "")
                grouped_by_ilova[top_level].append(item)

        statement_columns = []
        for ilova_order in sorted(grouped_by_ilova.keys(), key=int):
            for item in grouped_by_ilova[ilova_order]:
                column = item.statement_column
                if not column:
                    continue

                inners_data = []
                for inner in item.inners.all():
                    value = inner.value
                    if self._is_org_name_column(column, lang):
                        value = org_name
                    inners_data.append({"id": str(inner.id), "value": value})

                statement_columns.append({
                    "statement_column_id": str(column.id),
                    "statement_column_name": get_translated_field(column, "title", lang),
                    "inners": inners_data
                })
        return statement_columns

    def get_report_items(self, report):
        lang = get_lang_code(self.context)
        org_name = self.get_organization_name(report)
        items = report.report_items.all().order_by("statement_column__ordering")
        statement_columns = self._get_grouped_statement_columns(items, lang, org_name)

        return [{
            "organization_id": "general",
            "organization_name": org_name,
            "statement_columns": statement_columns
        }]

    def get_children_reports(self, report):
        if not report.region:
            return []

        lang = get_lang_code(self.context)
        # Deadline cheklovisiz: barcha ACCEPTED individual reportlarni chiqaramiz
        children = Report.objects.filter(
            statement=report.statement,
            is_general=False,
            is_individual_general=False,
            is_report=True,
            region=report.region,
            status=Report.StatusChoices.ACCEPTED
        ).order_by('-created_at').select_related(
            "organization", "statement", "sent_by", "sent_by_org"
        ).prefetch_related(
            "report_items__statement_column",
            "report_items__inners"
        )

        result = []
        for child in children:
            items = child.report_items.all().order_by("statement_column__ordering")
            org_name = get_translated_field(child.organization, "name", lang)
            statement_columns = self._get_grouped_statement_columns(items, lang, org_name)

            result.append({
                "id": str(child.id),
                "organization_name": org_name,
                "report_items": [{
                    "organization_id": str(child.organization.id),
                    "organization_name": org_name,
                    "statement_columns": statement_columns
                }],
                "sent_by_full_name": child.sent_by.full_name if child.sent_by else None,
                "sent_by_org_name": get_translated_field(child.sent_by_org, "name", lang) if child.sent_by_org else None,
                "sent_by_role": child.sent_by_role
            })

        return result
