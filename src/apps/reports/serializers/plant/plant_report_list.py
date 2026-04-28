import re
from uuid import UUID

from django.utils.translation import gettext_lazy as _

from apps.reports.models import StatementColumn, Report
from apps.reports.serializers.reports import ReportListSerializer
from apps.reports.services.quarter_validator import DaromadQuarterService
from apps.utils.translation import get_lang_code, get_translated_field


class PlantReportListSerializer(ReportListSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)

        if DaromadQuarterService.is_daromad_report(instance):
            data["quarter"] = instance.quarter
            data["current_quarter"] = instance.current_quarter
            data["quarter_info"] = {
                "quarter_1_status": instance.quarter_1_status,
                "quarter_2_status": instance.quarter_2_status,
                "quarter_3_status": instance.quarter_3_status,
                "quarter_4_status": instance.quarter_4_status,
                "quarter_1_dates": DaromadQuarterService.get_quarter_dates(instance, "q1"),
                "quarter_2_dates": DaromadQuarterService.get_quarter_dates(instance, "q2"),
                "quarter_3_dates": DaromadQuarterService.get_quarter_dates(instance, "q3"),
                "quarter_4_dates": DaromadQuarterService.get_quarter_dates(instance, "q4"),
            }
        else:
            data["quarter"] = None
            data["current_quarter"] = None
            data["quarter_info"] = None

        return data

    def get_report_items(self, report):
        lang = get_lang_code(self.context)

        request = self.context.get("request")
        is_user_input_filter = None
        if request:
            raw = request.query_params.get("is_user_input")
            if raw is not None:
                raw = str(raw).strip().lower()
                if raw in ("true", "1"):
                    is_user_input_filter = True
                elif raw in ("false", "0"):
                    is_user_input_filter = False

        if report.is_general:
            organization_id = "general"
            organization_name = _("Viloyat darajasidagi Jami")
        elif getattr(report, "is_individual_general", False):
            organization_id = "individual"
            organization_name = (
                f"{get_translated_field(report.organization, 'name', lang)} – {_('Tashkilot Jami')}"
            )
        elif report.is_republic:
            organization_id = "republic"
            organization_name = {
                "uz": "Respublika Jami",
                "ru": "Республиканский итог",
            }.get(lang, "Respublika Jami")
        else:
            organization_id = str(report.organization.id) if report.organization else "unknown"
            organization_name = (
                get_translated_field(report.organization, "name", lang)
                if report.organization else _("Nomaʼlum tashkilot")
            )

        items = list(report.report_items.all())

        if is_user_input_filter is not None:
            items = [
                i for i in items
                if i.statement_column and i.statement_column.is_user_input == is_user_input_filter
            ]

        def ordering_key(ordering: str):
            if not ordering:
                return []
            return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", ordering)]

        items.sort(key=lambda i: ordering_key(i.statement_column.ordering or ""))

        # Serializer contextdan ishlatamiz — har report uchun qayta query yo‘q
        column_map = self.context.get("statement_columns", {})

        def get_top_level_ordering(ordering: str) -> str:
            return ordering.split(".")[0] if ordering else "0"

        grouped_by_ilova = {}
        for item in items:
            column = item.statement_column
            if column is None:
                continue
            top_level = get_top_level_ordering(column.ordering)
            grouped_by_ilova.setdefault(top_level, []).append(item)

        statement_columns = []

        def ilova_sort_key(value: str):
            try:
                return int(value)
            except Exception:
                return value

        for ilova_ordering in sorted(grouped_by_ilova.keys(), key=ilova_sort_key):
            for item in grouped_by_ilova[ilova_ordering]:
                column = item.statement_column
                if column is None:
                    continue

                inner_values = []
                for inner in item.inners.all():
                    val = inner.value
                    inner_data = {"id": str(inner.id)}

                    if inner.plant:
                        inner_data.update({
                            "plant_id": str(inner.plant.id),
                            "plant_name": get_translated_field(inner.plant, "name", lang),
                            "value": val,
                        })
                    elif column.is_organization:
                        try:
                            UUID(str(val))
                            val = organization_name
                        except Exception:
                            val = _("Nomaʼlum tashkilot")
                        inner_data["value"] = val
                    else:
                        inner_data["value"] = val

                    inner_values.append(inner_data)

                statement_columns.append({
                    "statement_column_id": str(column.id),
                    "statement_column_name": self.get_full_column_path(column, lang, column_map),
                    "is_organization": column.is_organization,
                    "status_plan": column.status_plan if column.status_plan else None,
                    "inners": inner_values,
                })

        return [{
            "organization_id": organization_id,
            "organization_name": organization_name,
            "statement_columns": statement_columns,
        }]