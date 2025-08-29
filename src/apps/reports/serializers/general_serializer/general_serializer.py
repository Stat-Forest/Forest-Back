from rest_framework import serializers
from apps.reports.models import ReportItemInner, Report
from apps.utils.translation import get_lang_code, get_translated_field
from apps.utils.services import RegionChoices
from collections import defaultdict
import re


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
        return f"{region_label} – Viloyat Jami"

    def get_report_items(self, report):
        lang = get_lang_code(self.context)

        items = list(
            report.report_items
            .select_related("statement_column")
            .prefetch_related("inners")
        )

        def ordering_key(ordering: str):
            if not ordering:
                return []
            return [int(part) if part.isdigit() else part for part in re.split(r'(\d+)', ordering)]

        items.sort(key=lambda i: ordering_key(i.statement_column.ordering or ""))

        def get_top_level_ordering(ordering: str) -> str:
            return ordering.split(".")[0] if ordering else "0"

        organization_id = "general"
        organization_name = self.get_organization_name(report)

        grouped_by_ilova = defaultdict(list)
        for item in items:
            column = item.statement_column
            if column is None:
                continue
            top_level = get_top_level_ordering(column.ordering)
            grouped_by_ilova[top_level].append(item)

        statement_columns = []
        for ilova_ordering in sorted(grouped_by_ilova.keys(), key=lambda x: int(x)):
            for item in grouped_by_ilova[ilova_ordering]:
                column = item.statement_column
                if column is None:
                    continue

                inner_values = []
                for inner in item.inners.all():
                    val = inner.value
                    column_title = getattr(column, f"title_{lang}", "").lower()

                    if column.is_organization and column_title in ["tashkilot nomi", "название организации"]:
                        val = organization_name

                    inner_values.append({"id": str(inner.id), "value": val})

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

    def get_children_reports(self, report):
        from apps.reports.models import Report  # avoid circular imports
        children = Report.objects.filter(
            statement=report.statement,
            deadline=report.deadline,
            is_general=False,
            is_individual_general=False,
            is_report=True,
            region=report.region,
        ).select_related("organization").prefetch_related("report_items__statement_column", "report_items__inners")

        lang = get_lang_code(self.context)
        result = []

        def ordering_key(ordering: str):
            if not ordering:
                return []
            return [int(part) if part.isdigit() else part for part in re.split(r'(\d+)', ordering)]

        for child in children:
            child_items = list(child.report_items.all())
            child_items.sort(key=lambda i: ordering_key(i.statement_column.ordering or ""))

            grouped_by_ilova = defaultdict(list)
            for item in child_items:
                top_level = item.statement_column.ordering.split(".")[0] if item.statement_column.ordering else "0"
                grouped_by_ilova[top_level].append(item)

            statement_columns = []
            for ilova_ordering in sorted(grouped_by_ilova.keys(), key=lambda x: int(x)):
                for item in grouped_by_ilova[ilova_ordering]:
                    column = item.statement_column
                    if column is None:
                        continue

                    inner_values = []
                    for inner in item.inners.all():
                        val = inner.value
                        column_title = getattr(column, f"title_{lang}", "").lower()

                        if column.is_organization and column_title in ["tashkilot nomi", "название организации"]:
                            val = get_translated_field(child.organization, "name", lang)

                        inner_values.append({"id": str(inner.id), "value": val})

                    statement_columns.append({
                        "statement_column_id": str(column.id),
                        "statement_column_name": get_translated_field(column, "title", lang),
                        "inners": inner_values
                    })

            result.append({
                "id": str(child.id),
                "organization_name": get_translated_field(child.organization, "name", lang),
                "report_items": [{
                    "organization_id": str(child.organization.id),
                    "organization_name": get_translated_field(child.organization, "name", lang),
                    "statement_columns": statement_columns
                }]
            })

        return result
