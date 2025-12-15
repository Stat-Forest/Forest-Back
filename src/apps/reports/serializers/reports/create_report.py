import uuid
from datetime import date

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.general.models import Organization
from apps.utils.services import PeriodChoices
from apps.reports.report_calculate import ALL_CALCULATORS
from apps.reports.services import aggregate_individual_report
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.utils.translation import get_lang_code, get_translated_field
from apps.reports.services.simple_ensure_plans import ensure_plans_exist_simple
from apps.reports.models import Report, ReportItem, StatementColumn, ReportItemInner
from apps.reports.services.report_calculate_expressions import calculate_by_expressions
from apps.logs.models import HistoryActionJournal



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

    class Meta:
        model = Report
        fields = [
            "id", "deadline",
            "report_items"
        ]

    def validate(self, attrs):
        deadline = attrs["deadline"]
        statement = deadline.statement
        report_items = attrs['report_items']
        user = self.context['request'].user
        organization = user.organization
        is_individual_general = attrs.get("is_individual_general", False)

        # 1. Duplicated reportni tekshir
        if not is_individual_general:
            exists = Report.objects.filter(
                organization=organization,
                statement=statement,
                deadline=deadline,
                is_individual_general=False
            ).exists()
            if exists:
                raise ValidationError(
                    "Bu tashkilot uchun bu hisobot turi va davr bo‘yicha hisobot mavjud."
                )

        ensure_plans_exist_simple(
            organization=organization,
            statement=statement
        )

        # 2. Userning organizationi shu deadlinega tegishli emasmi?
        if not deadline.organizations.filter(id=user.organization.id).exists():
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
            if year > today.year or (year == today.year and month >= today.month):
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
            if year >= today.year:
                raise CustomExceptionError(400, {'submit_at': _('You can only submit for past years.')})

        # 5. Report allaqachon mavjudmi?
        if Report.objects.filter(
                organization=user.organization,
                statement=statement,
                deadline=deadline,
                is_individual_general=False,
                is_report=True
        ).exists():
            raise CustomExceptionError(400, {'report': _('This report already exists.')})

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        items_data = validated_data.pop("report_items")
        deadline = validated_data["deadline"]

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
            for item in items_data:
                col_id = item["statement_column"]
                column = columns_map.get(col_id)

                if not column:
                    raise serializers.ValidationError({"detail": f"Invalid column {col_id}"})

                inners_data = item.get("inners", [])

                # === ORGANIZATION USTUNI ===
                if column.is_organization:
                    if not inners_data or "value" not in inners_data[0]:
                        raise serializers.ValidationError(
                            {"detail": f"Organization inners required for column {col_id}"}
                        )
                    current_org_id = inners_data[0]["value"]
                    org_instance = Organization.objects.get(id=current_org_id)

                    report_key = (current_org_id, str(column.statement.id))

                    report = Report.objects.filter(
                        organization=org_instance,
                        statement=column.statement,
                        deadline=deadline,
                        is_individual_general=False
                    ).first()

                    if not report:
                        report = Report.objects.create(
                            organization=org_instance,
                            statement=column.statement,
                            deadline=deadline,
                            region=org_instance.region,
                            status=Report.StatusChoices.SAVED,
                            created_by=user
                        )

                        HistoryActionJournal.objects.create(
                            user=user,
                            action='add',
                            model_name='Report',
                            object_id=report.id,
                            object_repr=str(report),
                            change_message="Hisobat yaraladi",
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
                    report, _ = Report.objects.get_or_create(
                        organization=org_instance,
                        statement=child_statement,
                        deadline=deadline,
                        defaults={
                            "status": Report.StatusChoices.SAVED,
                            "region": org_instance.region
                        }
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
                    report_inners_buffer.append(
                        ReportItemInner(
                            report_item_id=report_item_id,
                            value=inner["value"]
                        )
                    )

            # === YIG‘ILGAN MA’LUMOTLARNI SAQLASH ===
            ReportItem.objects.bulk_create(report_items_buffer, batch_size=1000)
            ReportItemInner.objects.bulk_create(report_inners_buffer, batch_size=2000)

            # === HISOBLASH VA JAMI REPORTLAR ===
            if reports_map:
                for report in reports_map.values():
                    statement = report.statement
                    statement_name = report.statement.name_uz
                    calculate_func = ALL_CALCULATORS.get(statement_name)

                    if calculate_func:
                        calculate_func(report)
                    elif statement.calculate_expression:
                        calculate_by_expressions(report)

                    aggregate_individual_report(report)

            return list(reports_map.values())