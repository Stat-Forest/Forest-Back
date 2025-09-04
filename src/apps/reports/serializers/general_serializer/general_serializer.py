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
    # sent_by_full_name = serializers.SerializerMethodField()
    # sent_by_org_name = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
            "organization_name",
            "report_items",
            "children_reports",
            # "sent_by_full_name",
            # "sent_by_org_name",
            # "sent_by_role"
        ]

    def get_organization_name(self, report):
        region_label = dict(RegionChoices.choices).get(report.region, "Nomaʼlum")
        lang = get_lang_code(self.context)

        if lang == "ru":
            return f"{region_label} – Вилоятный итог"
        return f"{region_label} – Viloyat Jami"

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
        organization_name = self.get_organization_name(report)

        items = report.report_items.all()

        def ordering_key(ordering):
            if not ordering:
                return []
            return [int(part) if part.isdigit() else part for part in re.split(r'(\d+)', ordering)]

        def get_top_level_ordering(ordering):
            return ordering.split(".")[0] if ordering else "0"

        items = sorted(items, key=lambda i: ordering_key(i.statement_column.ordering or ""))

        grouped_by_ilova = defaultdict(list)
        for item in items:
            col = item.statement_column
            if col:
                top_level = get_top_level_ordering(col.ordering)
                grouped_by_ilova[top_level].append(item)

        statement_columns = []
        for ilova_order in sorted(grouped_by_ilova.keys(), key=int):
            for item in grouped_by_ilova[ilova_order]:
                column = item.statement_column
                if not column:
                    continue

                col_title = getattr(column, f"title_{lang}", "").strip().lower()
                inners = []

                for inner in item.inners.all():
                    val = inner.value
                    if column.is_organization and col_title in ["tashkilot nomi", "название организации", "наименование организации"]:
                        val = organization_name
                    inners.append({
                        "id": str(inner.id),
                        "value": val
                    })

                statement_columns.append({
                    "statement_column_id": str(column.id),
                    "statement_column_name": getattr(column, f"title_{lang}", ""),
                    "inners": inners
                })

        return [{
            "organization_id": "general",
            "organization_name": organization_name,
            "statement_columns": statement_columns
        }]

    def get_children_reports(self, report):
        from apps.reports.models import Report

        if not report.region:
            return []

        lang = get_lang_code(self.context)

        # ✅ Children reports queryset
        children = Report.objects.filter(
            statement=report.statement,
            deadline=report.deadline,
            is_general=False,
            is_individual_general=False,
            is_report=True,
            region=report.region
        ).select_related(
            "organization", "statement", "sent_by", "sent_by_org"
        ).prefetch_related(
            "report_items__statement_column",
            "report_items__inners"
        )

        def ordering_key(ordering):
            if not ordering:
                return []
            return [int(part) if part.isdigit() else part for part in re.split(r'(\d+)', ordering)]

        result = []

        for child in children:
            items = sorted(
                child.report_items.all(),
                key=lambda i: ordering_key(i.statement_column.ordering or "")
            )

            # ✅ Group by top-level ilova (e.g. 1., 2., 3.)
            grouped_by_ilova = defaultdict(list)
            for item in items:
                col = item.statement_column
                if col and col.ordering:
                    top_level = col.ordering.split(".")[0]
                    grouped_by_ilova[top_level].append(item)

            # ✅ Tashkilot nomi tarjimada
            org_name = get_translated_field(child.organization, "name", lang)

            statement_columns = []
            for ilova_order in sorted(grouped_by_ilova.keys(), key=int):
                for item in grouped_by_ilova[ilova_order]:
                    column = item.statement_column
                    if not column:
                        continue

                    col_title = getattr(column, f"title_{lang}", "").strip().lower()
                    inners = []

                    for inner in item.inners.all():
                        val = inner.value
                        # ✅ Tashkilot nomini tarjimada ko‘rsatish
                        if column.is_organization and col_title in ["tashkilot nomi", "название организации",
                                                                    "наименование организации"]:
                            val = org_name

                        inners.append({
                            "id": str(inner.id),
                            "value": val
                        })

                    statement_columns.append({
                        "statement_column_id": str(column.id),
                        "statement_column_name": getattr(column, f"title_{lang}", ""),
                        "inners": inners
                    })

            result.append({
                "id": str(child.id),
                "organization_name": org_name,
                "report_items": [{
                    "organization_id": str(child.organization.id),
                    "organization_name": org_name,
                    "statement_columns": statement_columns
                }],
                "sent_by_full_name": child.sent_by.full_name if child.sent_by else None,
                "sent_by_org_name": get_translated_field(child.sent_by_org, "name",
                                                         lang) if child.sent_by_org else None,
                "sent_by_role": child.sent_by_role
            })

        return result