import re
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from apps.reports.models import Report, StatementColumn
from apps.utils.services import RegionChoices
from apps.utils.translation import get_lang_code, get_translated_field


class ReportListSerializer(serializers.ModelSerializer):
    period = serializers.SerializerMethodField()
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

    def get_period(self, obj):
        lang = self.context.get("lang", "uz")
        period = obj.statement.period

        # Ixtiyoriy — tarjima qilish
        period_map = {
            "monthly": {"uz": "Oylik", "ru": "Ежемесячно"},
            "quarterly": {"uz": "Har chorakda", "ru": "Ежеквартально"},
            "yearly": {"uz": "Yillik", "ru": "Ежегодно"},
            "weekly": {"uz": "Haftalik", "ru": "Еженедельно"},
            "daily": {"uz": "Kunlik", "ru": "Ежедневно"},
        }

        return period_map.get(period, {}).get(lang, period)

    def get_report_items(self, report):
        lang = get_lang_code(self.context)

        items = list(
            report.report_items
            .select_related("statement_column__parent")
            .prefetch_related("inners")
            .all()
        )

        def ordering_key(ordering: str):
            if not ordering:
                return []
            return [int(part) if part.isdigit() else part for part in re.split(r'(\d+)', ordering)]

        items.sort(key=lambda i: ordering_key(i.statement_column.ordering or ""))

        def get_top_level_ordering(ordering: str) -> str:
            return ordering.split(".")[0] if ordering else "0"

        if report.is_general:
            organization_id = "general"
            organization_name = _("Viloyat darajasidagi Jami")
        elif getattr(report, "is_individual_general", False):
            organization_id = "individual"
            organization_name = f"{get_translated_field(report.organization, 'name', lang)} – {_('Tashkilot Jami')}"
        elif report.is_republic:
            organization_id = "republic"
            organization_name = {
                "uz": "Respublika Jami",
                "ru": "Республиканский итог"
            }.get(lang, "uz")
        else:
            organization_id = str(report.organization.id) if report.organization else "unknown"
            organization_name = get_translated_field(report.organization, "name", lang) if report.organization else _("Nomaʼlum tashkilot")

        # 🧠 Cache all statement columns for fast path generation
        all_columns = StatementColumn.objects.filter(statement=report.statement).select_related("parent")
        column_map = {str(col.id): col for col in all_columns}

        grouped_by_ilova = {}
        for item in items:
            column = item.statement_column
            if column is None:
                continue

            top_level = get_top_level_ordering(column.ordering)
            grouped_by_ilova.setdefault(top_level, []).append(item)

        statement_columns = []

        for ilova_ordering in sorted(grouped_by_ilova.keys(), key=lambda x: int(x)):
            for item in grouped_by_ilova[ilova_ordering]:
                column = item.statement_column
                if column is None:
                    continue

                inner_values = []
                for inner in item.inners.all():
                    val = inner.value

                    if column.is_organization:
                        col_title = getattr(column, f"title_{lang}", "").strip().lower()
                        if col_title in ["tashkilot nomi", "наименование организации", "название организации"]:
                            val = get_translated_field(report.organization, "name", lang)

                            if report.is_individual_general:
                                val = f"{_('Tashkilot Jami')}"
                            elif report.is_general:
                                region_label = dict(RegionChoices.choices).get(report.region, "Nomaʼlum")
                                val = f"{region_label} – {_('Viloyat Jami')}"
                            elif report.is_republic:
                                val = {
                                    "uz": "Respublika Jami",
                                    "ru": "Республиканский итог"
                                }.get(lang, "Respublika Jami")

                    inner_values.append({"id": str(inner.id), "value": val})

                statement_columns.append({
                    "statement_column_id": str(column.id),
                    "statement_column_name": self.get_full_column_path(column, lang, column_map),
                    "inners": inner_values
                })

        data = [{
            "organization_id": organization_id,
            "organization_name": organization_name,
            "statement_columns": statement_columns
        }]

        data.sort(key=lambda item: (
            0 if item["organization_id"] not in ["individual", "general", "republic"]
            else 1 if item["organization_id"] == "individual"
            else 2 if item["organization_id"] == "general"
            else 3
        ))

        return data

    def get_full_column_path(self, column: StatementColumn, lang: str, column_map: dict) -> str:
        path = []
        while column:
            title = getattr(column, f"title_{lang}", None)
            if title:
                path.append(title.strip())
            column = column_map.get(str(column.parent_id)) if column.parent_id else None
        return " – ".join(reversed(path))
