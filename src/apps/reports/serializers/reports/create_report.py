import uuid
from datetime import date

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.general.models import Organization
from apps.utils.services import PeriodChoices
from apps.logs.models import HistoryActionJournal
from apps.reports.report_calculate import ALL_CALCULATORS
from apps.reports.services import aggregate_individual_report
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.utils.translation import get_lang_code, get_translated_field
from apps.reports.services.simple_ensure_plans import ensure_plans_exist_simple
from apps.reports.services.change_coma_to_dote import normalize_decimal_input_dote
from apps.reports.models import Report, ReportItem, StatementColumn, ReportItemInner
from apps.reports.services.report_calculate_expressions import calculate_by_expressions


class ReportItemInnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportItemInner
        fields = ["id", "value"]


class ReportItemSerializer(serializers.ModelSerializer):
    inners = ReportItemInnerSerializer(many=True)

    class Meta:
        model = ReportItem
        fields = ["statement_column", "inners"]


# 12 ta viloyat, 1ta shahar, qoraqol respublikasi. boshqa tashkilotlar.
class ReportCreateSerializer(serializers.ModelSerializer):
    report_items = serializers.ListField(write_only=True)
    source_report = serializers.UUIDField(
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Report
        fields = [
            "id", "deadline", "report_season", "foot_note", "source_report", "report_items"
        ]

    def validate(self, attrs):
        deadline = attrs["deadline"]
        statement = deadline.statement
        report_items = attrs['report_items']
        user = self.context['request'].user
        user_org = user.organization
        is_individual_general = attrs.get("is_individual_general", False)
        report_season = attrs.get("report_season")

        # Detect svodka statement and resolve organization from source_report
        stmt_name_uz = (getattr(statement, "name_uz", "") or "").strip()
        is_svodka_stmt = stmt_name_uz == "Ko'chat va Nihol Yetishtirish Jami"
        resolved_org = user_org
        source_report_obj = None
        if is_svodka_stmt:
            source_report_id = attrs.get("source_report")
            if not source_report_id:
                raise ValidationError({"source_report": _("Svodka uchun manba report (source_report) majburiy")})

            # Fetch and validate source report
            try:
                source_report_obj = Report.objects.select_related("statement", "organization", "deadline").get(id=source_report_id)
            except Report.DoesNotExist:
                raise ValidationError({"source_report": _("Manba report topilmadi")})

            base_name_uz = (getattr(source_report_obj.statement, "name_uz", "") or "").strip()
            if base_name_uz != "Ko‘chat va Nihol":
                raise ValidationError({"source_report": _("Manba report 'Ko‘chat va Nihol' bo‘lishi shart")})

            if source_report_obj.organization_id != user_org.id:
                raise ValidationError({"source_report": _("Manba report boshqa tashkilotga tegishli")})

            # Compare years of submit_at
            def _extract_year(submit_at_val: str) -> int:
                if not submit_at_val:
                    return 0
                s = str(submit_at_val)
                try:
                    return int(s.split("-")[0])
                except Exception:
                    try:
                        return int(s)
                    except Exception:
                        return 0

            src_year = _extract_year(getattr(source_report_obj.deadline, "submit_at", ""))
            tgt_year = _extract_year(getattr(deadline, "submit_at", ""))
            if src_year and tgt_year and src_year != tgt_year:
                raise ValidationError({"source_report": _("Manba report yili bilan svodka yili bir xil bo‘lishi kerak")})

            resolved_org = source_report_obj.organization

        # 1. Duplicated reportni tekshir
        if not is_individual_general:
            qs = Report.objects.filter(
                organization=resolved_org,
                statement=statement,
                deadline=deadline,
                is_individual_general=False
            )

            if report_season is None:
                qs = qs.filter(report_season__isnull=True)
            else:
                qs = qs.filter(report_season=report_season)

            if qs.exists():
                raise ValidationError(
                    "Bu tashkilot uchun bu hisobot turi va davr bo‘yicha hisobot mavjud."
                )

        ensure_plans_exist_simple(
            organization=resolved_org,
            statement=statement
        )

        # 2. Userning organizationi shu deadlinega tegishli emasmi?
        if not deadline.organizations.filter(id=user_org.id).exists():
            raise CustomExceptionError(400, _('Sizga bu deadline uchun ruxsat berilmagan.'))

        print("🧪 deadline:", deadline)
        print("🧪 deadline.submit_at:", deadline.submit_at)

        # 3. StatementColumn'lar tekshiriladi
        column_ids = [item['statement_column'] for item in report_items]
        statement_columns = StatementColumn.objects.select_related('parent').in_bulk(column_ids)

        def get_week_of_month(day):
            first_day = day.replace(day=1)
            adjusted_dom = day.day + first_day.weekday()
            return (adjusted_dom - 1) // 7 + 1

        # 4. Deadline vaqt tekshiruvi
        today = date.today()
        submit_at = deadline.submit_at

        if statement.period == PeriodChoices.KUNLIK:
            report_day = date.fromisoformat(submit_at)
            if report_day >= today:
                raise CustomExceptionError(400, {'submit_at': _('You can only submit for past days.')})

        elif statement.period == PeriodChoices.HAFTALIK:
            # Kutilyotgan format: YYYY-MM-HAFTALIK_x
            import re
            match = re.match(r'^(?P<year>\d{4})-(?P<month>\d{2})-HAFTALIK_(?P<week>[1-4])$', submit_at)
            if not match:
                raise CustomExceptionError(400, {'submit_at': _('Invalid weekly format. Must be YYYY-MM-HAFTALIK_x')})

            year = int(match.group('year'))
            month = int(match.group('month'))
            week = int(match.group('week'))

            if year > today.year or (year == today.year and month > today.month):
                raise CustomExceptionError(400, {'submit_at': _('You can only submit for past weeks.')})
            if year == today.year and month == today.month and week >= get_week_of_month(today):
                raise CustomExceptionError(400, {'submit_at': _('You can only submit for past weeks.')})



        elif statement.period == PeriodChoices.OYLIK:
            parts = submit_at.split('-')
            if len(parts) != 2 or not parts[1].isdigit():
                raise CustomExceptionError(400, {'submit_at': _('Invalid monthly format. Must be YYYY-MM')})
            try:
                year, month = map(int, parts)
            except ValueError:
                raise CustomExceptionError(400, {'submit_at': _('Invalid monthly numbers.')})
            if year > today.year or (year == today.year and month > today.month):
                raise CustomExceptionError(400, {'submit_at': _('You can only submit for past months.')})

        elif statement.period == PeriodChoices.CHORAKLIK:
            # Kutilyotgan format: YYYY-CHORAK_x
            import re
            match = re.match(r'^(?P<year>\d{4})-CHORAK_(?P<quarter>[1-4])$', submit_at)
            if not match:
                raise CustomExceptionError(400, {'submit_at': _('Invalid quarterly format. Must be YYYY-CHORAK_x')})

            year = int(match.group('year'))
            quarter = int(match.group('quarter'))
            current_quarter = (today.month - 1) // 3 + 1
            if year > today.year or (year == today.year and quarter >= current_quarter):
                raise CustomExceptionError(400, {'submit_at': _('You can only submit for past quarters.')})

        elif statement.period == PeriodChoices.YILLIK:
            year = int(submit_at)
            if year > today.year:
                raise CustomExceptionError(400, {'submit_at': _('You can only submit for past years.')})

        # 5. Report allaqachon mavjudmi?
        qs = Report.objects.filter(
            organization=user.organization,
            statement=statement,
            deadline=deadline,
            is_individual_general=False,
            is_report=True
        )

        if report_season is None:
            qs = qs.filter(report_season__isnull=True)
        else:
            qs = qs.filter(report_season=report_season)

        if qs.exists():
            raise CustomExceptionError(400, {'report': _('This report already exists.')})

        # Attach resolved org and source_report for create()
        attrs["_resolved_organization"] = resolved_org
        if source_report_obj:
            attrs["_source_report_obj"] = source_report_obj

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        items_data = validated_data.pop("report_items")
        deadline = validated_data["deadline"]
        report_season = validated_data.get("report_season")
        foot_note = validated_data.get("foot_note")
        resolved_org = validated_data.pop("_resolved_organization", getattr(user, "organization", None))
        source_report_obj = validated_data.pop("_source_report_obj", None)

        column_ids = [item["statement_column"] for item in items_data]
        columns_map = {
            str(c.id): c
            for c in StatementColumn.objects.filter(id__in=column_ids).select_related("statement")
        }
        reports_map = {}
        current_org_id = None

        report_items_buffer = []
        report_inners_buffer = []

        with transaction.atomic():
            # Detect svodka once for this request
            stmt_name_uz = (getattr(deadline.statement, "name_uz", "") or "").strip()
            is_svodka_stmt = stmt_name_uz == "Ko'chat va Nihol Yetishtirish Jami"
            if is_svodka_stmt and resolved_org and not current_org_id:
                current_org_id = str(resolved_org.id)

            for item in items_data:
                col_id = item["statement_column"]
                column = columns_map.get(col_id)

                if not column:
                    raise serializers.ValidationError({"detail": f"Invalid column {col_id}"})

                inners_data = item.get("inners", [])

                # === ORGANIZATION USTUNI ===
                if column.is_organization:
                    if is_svodka_stmt:
                        current_org_id = str(resolved_org.id)
                        org_instance = resolved_org
                    else:
                        if not inners_data or "value" not in inners_data[0]:
                            raise serializers.ValidationError(
                                {"detail": f"Organization inners required for column {col_id}"}
                            )
                        current_org_id = inners_data[0]["value"]
                        org_instance = Organization.objects.get(id=current_org_id)

                    report_key = (current_org_id, str(column.statement.id))

                    qs = Report.objects.filter(
                        organization=org_instance,
                        statement=column.statement,
                        deadline=deadline,
                        is_individual_general=False
                    )

                    if report_season is None:
                        qs = qs.filter(report_season__isnull=True)
                    else:
                        qs = qs.filter(report_season=report_season)

                    report = qs.first()

                    if not report:
                        report = Report.objects.create(
                            organization=org_instance,
                            statement=column.statement,
                            deadline=deadline,
                            report_season=report_season,
                            region=org_instance.region,
                            status=Report.StatusChoices.SAVED,
                            created_by=user,
                            foot_note=foot_note,
                            source_report=source_report_obj if is_svodka_stmt else None,
                        )

                        HistoryActionJournal.objects.create(
                            user=user,
                            action='add',
                            model_name='Report',
                            object_id=report.id,
                            object_repr=str(report),
                            change_message="Hisobot yaraldi",
                        )

                    reports_map[report_key] = report

                    report_item_id = uuid.uuid4()
                    report_items_buffer.append(
                        ReportItem(
                            id=report_item_id,
                            report=report,
                            statement_column=column
                        )
                    )
                    for inner in inners_data:
                        inner_value = inner["value"]

                        lang = get_lang_code(self.context)
                        column_title = getattr(column, f"title_{lang}", "")

                        if column_title.lower() in ["tashkilot nomi", "название организации",
                                                    "наименование организации"]:
                            if report.is_individual_general or report.is_general:
                                inner_value = get_translated_field(report.organization, "name", lang)
                                suffix = " – Tashkilot Jami" if report.is_individual_general else " – Viloyat Jami"
                                inner_value = f"{inner_value}{suffix}"
                            else:
                                inner_value = get_translated_field(report.organization, "name", lang)

                        report_inners_buffer.append(
                            ReportItemInner(
                                report_item_id=report_item_id,
                                value=inner_value
                            )
                        )
                    continue

                # === ODDIY COLUMN (is_organization=False) ===
                if not current_org_id:
                    raise serializers.ValidationError({
                        "detail": "Organization column required before data columns"
                    })

                child_statement = column.statement
                report_key = (current_org_id, str(child_statement.id))

                if report_key not in reports_map:
                    org_instance = Organization.objects.get(id=current_org_id)
                    qs = Report.objects.filter(
                        organization=org_instance,
                        statement=child_statement,
                        deadline=deadline,
                        is_individual_general=False
                    )

                    if report_season is None:
                        qs = qs.filter(report_season__isnull=True)
                    else:
                        qs = qs.filter(report_season=report_season)

                    report = qs.first()

                    if not report:
                        report = Report.objects.create(
                            organization=org_instance,
                            statement=child_statement,
                            deadline=deadline,
                            report_season=report_season,
                            status=Report.StatusChoices.SAVED,
                            region=org_instance.region,
                            foot_note=foot_note,
                            source_report=source_report_obj if is_svodka_stmt else None,
                        )

                    reports_map[report_key] = report

                report = reports_map[report_key]

                report_item_id = uuid.uuid4()
                report_items_buffer.append(
                    ReportItem(
                        id=report_item_id,
                        report=report,
                        statement_column=column
                    )
                )
                for inner in inners_data:
                    raw_value = inner["value"]
                    normalized_value = normalize_decimal_input_dote(raw_value)
                    report_inners_buffer.append(
                        ReportItemInner(
                            report_item_id=report_item_id,
                            value=normalized_value
                        )
                    )

            with transaction.atomic():

                # 1. bulk saqlash
                ReportItem.objects.bulk_create(report_items_buffer, batch_size=1000)
                ReportItemInner.objects.bulk_create(report_inners_buffer, batch_size=2000)

                # 2. 🔑 MUHIM JOY
                def run_after_commit():
                    for report in reports_map.values():
                        print("STATEMENT NAME:", repr(report.statement.name_uz))
                        statement = report.statement
                        calculate_func = ALL_CALCULATORS.get(statement.name_uz)
                        print("CALCULATOR FOUND:", calculate_func)

                        if calculate_func:
                            calculate_func(report)
                        elif statement.calculate_expression:
                            calculate_by_expressions(report)

                        aggregate_individual_report(report)

                transaction.on_commit(run_after_commit)

            return list(reports_map.values())