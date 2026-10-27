import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.utils.services import RegionChoices
from apps.reports.models import Report, StatementColumn
from apps.utils.translation import get_lang_code, get_translated_field
from apps.reports.services.quarter_validator import DaromadQuarterService
from apps.reports.services.report_items_loader import items_from_prefetch


class ReportListSerializer(serializers.ModelSerializer):
    time_status = serializers.SerializerMethodField()
    period = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    report_items = serializers.SerializerMethodField()
    statement_name = serializers.SerializerMethodField()
    sent_by_full_name = serializers.SerializerMethodField()
    sent_by_org_name = serializers.SerializerMethodField()
    signature = serializers.SerializerMethodField()
    submit_at = serializers.SerializerMethodField()
    deadline_at = serializers.SerializerMethodField()
    # exporter helpers
    is_individual_general = serializers.SerializerMethodField()
    is_general = serializers.SerializerMethodField()
    is_republic = serializers.SerializerMethodField()
    is_plant_based = serializers.SerializerMethodField()
    row_number = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            "id", "organization", "organization_name",
            "statement", "statement_name",
            "deadline", "submit_at",
            "period", "status",
            "created_at", "cancel_reason",
            "cancelled_at", "sent_at", "accepted_at",
            "deadline_at",
            "report_items", "time_status", "report_season", "foot_note",
            "sent_by_full_name", "sent_by_org_name", "sent_by_role", "signature",
            "is_individual_general", "is_general", "is_republic", "is_plant_based", "row_number",
        )

    # ---------------------
    # SIMPLE FIELDS
    # ---------------------

    def get_deadline_at(self, obj):
        return obj.deadline.deadline_at if obj.deadline else None

    def get_time_status(self, obj):
        if obj.time_status:
            return obj.get_time_status_display()
        return None

    def get_submit_at(self, obj):
        return obj.deadline.submit_at if obj.deadline else None

    def get_organization_name(self, obj):
        lang = get_lang_code(self.context)

        if getattr(obj, "is_general", False):
            region_label = dict(RegionChoices.choices).get(obj.region, "")
            return f"{region_label} – {_('Viloyat Jami')}"

        if getattr(obj, "is_republic", False):
            return {"uz": "Respublika Jami", "ru": "Республиканский итог"}.get(lang, "Respublika Jami")

        return get_translated_field(obj.organization, "name", lang)

    def get_statement_name(self, obj):
        lang = get_lang_code(self.context)
        return get_translated_field(obj.statement, "name", lang)

    def get_sent_by_full_name(self, obj):
        return obj.sent_by.full_name if obj.sent_by else None

    def get_signature(self, obj):
        """Joriy yuborishning E-imzo imzosi (Daromadda — joriy chorak uchun)."""
        if obj.status not in (Report.StatusChoices.SENT, Report.StatusChoices.ACCEPTED) and not (
            DaromadQuarterService.is_daromad_report(obj) and obj.current_quarter
        ):
            return None
        quarter = obj.current_quarter if DaromadQuarterService.is_daromad_report(obj) else None
        # signatures -created_at tartibida; prefetch bo'lsa qo'shimcha so'rov yo'q
        for sig in obj.signatures.all():
            if sig.is_valid and (sig.quarter or None) == (quarter or None):
                return {
                    "id": str(sig.id),
                    "signer_full_name": sig.signer_cn,
                    "signer_tin": sig.signer_tin,
                    "signed_at": sig.signed_at,
                    "verify_path": f"/verify/{sig.id}",
                }
        return None

    def get_sent_by_org_name(self, obj):
        lang = get_lang_code(self.context)
        return get_translated_field(obj.sent_by_org, "name", lang) if obj.sent_by_org else None

    def get_period(self, obj):
        lang = self.context.get("lang", "uz")
        period = obj.statement.period

        period_map = {
            "monthly": {"uz": "Oylik", "ru": "Ежемесячно"},
            "quarterly": {"uz": "Har chorakda", "ru": "Ежеквартально"},
            "yearly": {"uz": "Yillik", "ru": "Ежегодно"},
            "weekly": {"uz": "Haftalik", "ru": "Еженедельно"},
            "daily": {"uz": "Kunlik", "ru": "Ежедневно"},
        }
        return period_map.get(period, {}).get(lang, period)

    # ---------------------
    # REPORT ITEMS (OPTIMIZED)
    # ---------------------

    def get_report_items(self, report: Report):
        if self.context.get("compact"):
            return []
        lang = get_lang_code(self.context)

        # View sahifadagi hisobotlar uchun item'larni values() bilan yuklab bergan bo'lsa
        # (items_by_report) — model obyektlari yaratilmaydi; aks holda prefetch'dan.
        preloaded = self.context.get("items_by_report")
        if preloaded is not None:
            items = preloaded.get(str(report.id), [])
        else:
            items = items_from_prefetch(report)

        def ordering_key(ordering: str):
            if not ordering:
                return []
            return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", ordering)]

        def get_top_level_ordering(ordering: str) -> str:
            return ordering.split(".")[0] if ordering else "0"

        # ORGANIZATION TYPES (o‘zgarmaydi)
        if report.is_general:
            organization_id = "general"
            organization_name = _("Viloyat darajasidagi Jami")
        elif getattr(report, "is_individual_general", False):
            organization_id = "individual"
            organization_name = f"{get_translated_field(report.organization, 'name', lang)} – {_('Tashkilot Jami')}"
        elif report.is_republic:
            organization_id = "republic"
            organization_name = {"uz": "Respublika Jami", "ru": "Республиканский итог"}.get(lang, "Respublika Jami")
        else:
            organization_id = str(report.organization.id) if report.organization else "unknown"
            organization_name = get_translated_field(report.organization, "name", lang) if report.organization else _("Nomaʼlum tashkilot")

        # ✅ StatementColumn preload context’dan
        preload = (self.context or {}).get("columns_by_statement_id") or {}
        stmt_id = str(getattr(report, "statement_id", report.statement.id))
        all_columns = preload.get(stmt_id)

        if not all_columns:
            # fallback (odatda bo‘lmasligi kerak)
            all_columns = list(
                StatementColumn.objects.filter(statement_id=report.statement_id).select_related("parent")
            )

        column_map = {str(col.id): col for col in all_columns}

        # Ustun bo'yicha tartiblash va ilova (yuqori daraja) bo'yicha guruhlash
        resolved = []
        for item in items:
            column = column_map.get(item["statement_column_id"]) if item["statement_column_id"] else None
            if column is None:
                continue
            resolved.append((column, item))
        resolved.sort(key=lambda pair: ordering_key(pair[0].ordering or ""))

        grouped_by_ilova = {}
        for column, item in resolved:
            top_level = get_top_level_ordering(column.ordering)
            grouped_by_ilova.setdefault(top_level, []).append((column, item))

        org_name_titles = {"tashkilot nomi", "наименование организации", "название организации"}
        statement_columns = []

        for ilova_ordering in sorted(grouped_by_ilova.keys(), key=lambda x: int(x) if x.isdigit() else 0):
            for column, item in grouped_by_ilova[ilova_ordering]:
                inner_values = []
                replace_org = column.is_organization and (
                    (getattr(column, f"title_{lang}", "") or "").strip().lower() in org_name_titles
                )
                # Tartib MUHIM: eksportda qator raqami shu ro'yxatning indeksidan olinadi
                # (loader (created_at, id) bo'yicha tartiblab beradi).
                for inner in item["inners"]:
                    val = inner["value"]
                    if replace_org:
                        # org name replacement logic o‘zgarmaydi
                        val = get_translated_field(report.organization, "name", lang)
                        if report.is_individual_general:
                            val = f"{_('Tashkilot Jami')}"
                        elif report.is_general:
                            region_label = dict(RegionChoices.choices).get(report.region, "Nomaʼlum")
                            val = f"{region_label} – {_('Viloyat Jami')}"
                        elif report.is_republic:
                            val = {"uz": "Respublika Jami", "ru": "Республиканский итог"}.get(lang, "Respublika Jami")
                    inner_values.append({"id": inner["id"], "value": val})

                statement_columns.append({
                    "statement_column_id": str(column.id),
                    "statement_column_name": self.get_full_column_path(column, lang, column_map),
                    "inners": inner_values,
                })

        return [{
            "organization_id": organization_id,
            "organization_name": organization_name,
            "statement_columns": statement_columns,
        }]

    # ---------------------
    # Exporter helper fields
    # ---------------------

    def get_is_individual_general(self, obj):
        return bool(getattr(obj, "is_individual_general", False))

    def get_is_general(self, obj):
        return bool(getattr(obj, "is_general", False))

    def get_is_republic(self, obj):
        return bool(getattr(obj, "is_republic", False))

    def get_is_plant_based(self, obj):
        return False

    def get_row_number(self, obj):
        row_map = self.context.get("row_number_map") or {}
        return row_map.get(str(obj.id), "")

    # ---------------------
    # COLUMN PATH
    # ---------------------

    def get_full_column_path(self, column: StatementColumn, lang: str, column_map: dict) -> str:
        path = []
        while column:
            title = getattr(column, f"title_{lang}", None)
            if title:
                path.append(title.strip())
            column = column_map.get(str(column.parent_id)) if column.parent_id else None
        return " – ".join(reversed(path))
