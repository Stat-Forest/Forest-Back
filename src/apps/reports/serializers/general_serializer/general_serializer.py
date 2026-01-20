import re
from collections import defaultdict
from rest_framework import serializers

from apps.base.serializers import CustomModelSerializer
from apps.utils.services import RegionChoices
from apps.reports.models import ReportItemInner, Report
from apps.utils.translation import get_lang_code, get_translated_field


class GeneralReportItemInnerSerializer(CustomModelSerializer):
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


class RegionalGeneralReportSerializer(CustomModelSerializer):
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_organization_name(self, report):
        lang = get_lang_code(self.context)

        # 🔴 Respublika Jami
        if report.is_republic:
            return "Итог Республики" if lang == "ru" else "Respublika Jami"

        # 🔵 Viloyat Jami
        region_label = dict(RegionChoices.choices).get(report.region, "Nomaʼlum")
        return f"{region_label} – {'Вилоятный итог' if lang == 'ru' else 'Viloyat Jami'}"

    def _ordering_key(self, ordering: str):
        if not ordering:
            return []
        return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", ordering)]

    def _get_top_level_ordering(self, ordering: str) -> str:
        return ordering.split(".")[0] if ordering else "0"

    def _is_org_name_column(self, column, lang: str) -> bool:
        title = getattr(column, f"title_{lang}", "").strip().lower()
        return (
            column.is_organization
            and title in {
                "tashkilot nomi",
                "название организации",
                "наименование организации",
            }
        )

    # ------------------------------------------------------------------
    # Core logic (NO ORM ACCESS HERE)
    # ------------------------------------------------------------------

    def _get_grouped_statement_columns(self, items, lang, org_name):
        """
        items: list[ReportItem]
        StatementColumn obyektlari faqat context["columns_by_id"] orqali olinadi
        """
        column_map = self.context["columns_by_id"]

        grouped_by_ilova = defaultdict(list)

        for item in items:
            column = column_map.get(item.statement_column_id)
            if not column:
                continue

            top_level = self._get_top_level_ordering(column.ordering)
            grouped_by_ilova[top_level].append((item, column))

        statement_columns = []

        for ilova_order in sorted(grouped_by_ilova.keys(), key=int):
            for item, column in grouped_by_ilova[ilova_order]:
                inners_data = []

                for inner in item.inners.all():
                    value = inner.value
                    if self._is_org_name_column(column, lang):
                        value = org_name

                    inners_data.append({
                        "id": str(inner.id),
                        "value": value,
                    })

                statement_columns.append({
                    "statement_column_id": str(column.id),
                    "statement_column_name": get_translated_field(column, "title", lang),
                    "inners": inners_data,
                })

        return statement_columns

    # ------------------------------------------------------------------
    # Public serializers
    # ------------------------------------------------------------------

    def get_report_items(self, report):
        lang = get_lang_code(self.context)
        org_name = self.get_organization_name(report)

        column_map = self.context["columns_by_id"]

        items = list(report.report_items.all())

        # ❗ ORM ordering emas, Python ordering
        items.sort(
            key=lambda i: self._ordering_key(
                column_map[i.statement_column_id].ordering
            )
        )

        statement_columns = self._get_grouped_statement_columns(
            items, lang, org_name
        )

        return [{
            "organization_id": "general",
            "organization_name": org_name,
            "statement_columns": statement_columns,
        }]

    def get_children_reports(self, report):
        if not report.region:
            return []

        lang = get_lang_code(self.context)
        column_map = self.context["columns_by_id"]

        children = (
            Report.objects.filter(
                statement=report.statement,
                is_general=False,
                is_individual_general=False,
                is_report=True,
                region=report.region,
                status=Report.StatusChoices.ACCEPTED,
            )
            .order_by("-created_at")
            .select_related(
                "organization",
                "statement",
                "sent_by",
                "sent_by_org",
            )
            .prefetch_related(
                "report_items",
                "report_items__inners",
            )
        )

        result = []

        for child in children:
            items = list(child.report_items.all())

            items.sort(
                key=lambda i: self._ordering_key(
                    column_map[i.statement_column_id].ordering
                )
            )

            org_name = get_translated_field(child.organization, "name", lang)

            statement_columns = self._get_grouped_statement_columns(
                items, lang, org_name
            )

            result.append({
                "id": str(child.id),
                "organization_name": org_name,
                "report_items": [{
                    "organization_id": str(child.organization.id),
                    "organization_name": org_name,
                    "statement_columns": statement_columns,
                }],
                "sent_by_full_name": child.sent_by.full_name if child.sent_by else None,
                "sent_by_org_name": (
                    get_translated_field(child.sent_by_org, "name", lang)
                    if child.sent_by_org else None
                ),
                "sent_by_role": child.sent_by_role,
            })

        return result

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.is_republic:
            data.pop("children_reports", None)

        return data