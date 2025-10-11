import re
from django.utils.translation import gettext_lazy as _
from apps.reports.models import StatementColumn
from apps.utils.translation import get_lang_code, get_translated_field
from apps.reports.serializers.reports import ReportListSerializer


class PlantReportListSerializer(ReportListSerializer):
    def get_report_items(self, report):
        lang = get_lang_code(self.context)

        # ✅ Oldindan olish
        items = list(
            report.report_items
            .select_related("statement_column__parent", "statement_column__statement")
            .prefetch_related("inners__plant")
        )

        def ordering_key(ordering: str):
            if not ordering:
                return []
            return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", ordering)]

        items.sort(key=lambda i: ordering_key(i.statement_column.ordering or ""))

        # ✅ Organization info
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
        statements = list({i.statement_column.statement for i in items})
        all_columns = (
            StatementColumn.objects.filter(statement__in=statements)
            .select_related("parent", "statement")
        )
        column_map = {str(col.id): col for col in all_columns}

        # ✅ Guruhlash
        grouped_by_statement = {}
        for item in items:
            statement_id = str(item.statement_column.statement.id)
            grouped_by_statement.setdefault(statement_id, []).append(item)

        # ✅ Natija
        grouped_data = []

        for statement_id, ilova_items in grouped_by_statement.items():
            statement = ilova_items[0].statement_column.statement
            ilova_name = get_translated_field(statement, "name", lang)
            statement_columns = []

            # 🟢 Tashkilot nomi uchun column
            org_col = next(
                (it.statement_column for it in ilova_items if it.statement_column.is_organization),
                None
            )
            if not org_col:
                # Agar innerlardan topilmasa, bazadan statement bo‘yicha olib kelamiz
                org_col = StatementColumn.objects.filter(
                    statement=statement,
                    is_organization=True
                ).first()

            if org_col:
                statement_columns.append({
                    "statement_column_id": str(org_col.id),
                    "statement_column_name": (
                        f"{ilova_name} – {self.get_full_column_path(org_col, lang, column_map)}"
                    ),
                    "inners": [{"value": organization_name}],
                })
            else:
                # Hali to‘liq setup qilinmagan bo‘lishi mumkin
                statement_columns.append({
                    "statement_column_id": None,
                    "statement_column_name": f"{ilova_name} – Tashkilot nomi",
                    "inners": [{"value": organization_name}],
                })

            # 🟢 Qolgan ustunlar (plant asosidagi)
            for item in ilova_items:
                column = item.statement_column
                if not column or column.is_organization:
                    continue

                inner_values = []
                for inner in item.inners.all():
                    if inner.plant:
                        inner_values.append({
                            "id": str(inner.id),
                            "plant_id": str(inner.plant.id),
                            "plant_name": get_translated_field(inner.plant, "name", lang),
                            "value": inner.value,
                        })
                    else:
                        inner_values.append({
                            "id": str(inner.id),
                            "value": inner.value,
                        })

                statement_columns.append({
                    "statement_column_id": str(column.id),
                    "statement_column_name": self.get_full_column_path(column, lang, column_map),
                    "inners": inner_values,
                })

            grouped_data.append({
                "organization_id": organization_id,
                "organization_name": organization_name,
                "statement_columns": statement_columns,
            })

        return grouped_data
