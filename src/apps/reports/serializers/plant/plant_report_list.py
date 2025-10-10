import re
from django.utils.translation import gettext_lazy as _
from apps.reports.models import StatementColumn
from apps.utils.services import RegionChoices
from apps.utils.translation import get_lang_code, get_translated_field
from apps.reports.serializers.reports import ReportListSerializer


class PlantReportListSerializer(ReportListSerializer):
    def get_report_items(self, report):
        lang = get_lang_code(self.context)

        # ✅ report_items va inner plant’larni olish
        items = list(
            report.report_items
            .select_related("statement_column__parent", "statement_column__statement")
            .prefetch_related("inners__plant")
            .all()
        )

        def ordering_key(ordering: str):
            if not ordering:
                return []
            return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", ordering)]

        items.sort(key=lambda i: ordering_key(i.statement_column.ordering or ""))

        # ✅ organization info
        if report.is_general:
            organization_id = "general"
            organization_name = _("Viloyat darajasidagi Jami")
        elif getattr(report, "is_individual_general", False):
            organization_id = "individual"
            organization_name = (
                f"{get_translated_field(report.organization, 'name', lang)} – "
                f"{_('Tashkilot Jami')}"
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

        # ✅ Column cache
        all_columns = (
            StatementColumn.objects.filter(statement__in=[i.statement_column.statement for i in items])
            .select_related("parent", "statement")
        )
        column_map = {str(col.id): col for col in all_columns}

        # ✅ Har bir statement (ilova) bo‘yicha guruhlash
        grouped_by_statement = {}
        for item in items:
            statement_id = str(item.statement_column.statement.id)
            grouped_by_statement.setdefault(statement_id, []).append(item)

        statement_columns = []

        # ✅ Har bir ilova uchun ma’lumotlarni chiqarish
        for statement_id, ilova_items in grouped_by_statement.items():
            # Ilova nomini olish (Ko‘chat-ilovasi / Nihol-ilovasi ...)
            ilova_name = get_translated_field(ilova_items[0].statement_column.statement, "name", lang)

            # 🟢 1. "Tashkilot nomi" columnni chiqarish
            org_col = next(
                (it.statement_column for it in ilova_items if it.statement_column.is_organization),
                None
            )
            if org_col:
                statement_columns.append({
                    "statement_column_id": str(org_col.id),
                    "statement_column_name": f"{ilova_name} – {self.get_full_column_path(org_col, lang, column_map)}",
                    "inners": [{"value": organization_name}],
                })

            # 🟢 2. Qolgan columnlarni chiqarish
            for item in ilova_items:
                column = item.statement_column
                if not column or column.is_organization:
                    continue

                inner_values = []
                for inner in item.inners.all():
                    if not inner.plant:
                        continue
                    inner_values.append({
                        "id": str(inner.id),
                        "plant_id": str(inner.plant.id),
                        "plant_name": get_translated_field(inner.plant, "name", lang),
                        "value": inner.value,
                    })

                statement_columns.append({
                    "statement_column_id": str(column.id),
                    "statement_column_name": self.get_full_column_path(column, lang, column_map),
                    "inners": inner_values,
                })

        # 🟢 Natijani yig‘ish
        data = [{
            "organization_id": organization_id,
            "organization_name": organization_name,
            "statement_columns": statement_columns,
        }]

        # Tartiblash
        data.sort(
            key=lambda item: (
                0
                if item["organization_id"] not in ["individual", "general", "republic"]
                else 1
                if item["organization_id"] == "individual"
                else 2
                if item["organization_id"] == "general"
                else 3
            )
        )

        return data
