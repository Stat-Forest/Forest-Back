import uuid

from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.reports.report_calculate import ALL_CALCULATORS
from apps.general.models import Organization
from apps.reports.models import Report, ReportItem, StatementColumn, ReportItemInner
from apps.reports.services import aggregate_individual_report
from apps.utils.translation import get_lang_code, get_translated_field


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
        organization = attrs.get("organization")
        statement = attrs.get("statement")
        deadline = attrs.get("deadline")
        is_individual_general = attrs.get("is_individual_general", False)

        if not is_individual_general:
            exists = Report.objects.filter(
                organization=organization,
                statement=statement,
                deadline=deadline,
                is_individual_general=False
            ).exists()

            if exists:
                raise ValidationError(
                    "Bu tashkilot uchun bu hisobot turi va deadline bo‘yicha allaqachon report mavjud."
                )
        return attrs

    def create(self, validated_data):
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
                            status=Report.StatusChoices.SAVED
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

                        if column_title.lower() in ["tashkilot nomi", "название организации"]:
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
                    statement_name = report.statement.name_uz
                    calculate_func = ALL_CALCULATORS.get(statement_name)
                    if calculate_func:
                        calculate_func(report)

                    aggregate_individual_report(report)

            return list(reports_map.values())

# class ReportCreateSerializer(serializers.ModelSerializer):
#     report_items = ReportItemCreateSerializer(many=True, write_only=True)
#     CACHE_KEY = 'report_organization'
#
#     class Meta:
#         model = Report
#         fields = ['id', 'deadline', 'report_items']
#
#     def validate_uuid(self, value):
#         try:
#             return UUID(str(value))
#         except ValueError:
#             raise CustomExceptionError(400, _('Organization ID must be a valid UUID.'))
#
#     def validate(self, attrs):
#         report_items = attrs['report_items']
#         deadline = attrs['deadline']
#         statement = deadline.statement
#         user = self.context['request'].user
#
#         # if not user.statement:
#         #     raise CustomExceptionError(400, _('User must have a statement to create report !'))
#         #
#         # if user.statement != statement.parent:
#         #     raise CustomExceptionError(400, _('User statement does not match deadline statement !'))
#
#         if not deadline.organizations.filter(id=user.organization.id).exists():
#             raise CustomExceptionError(400, _('User organization is not related to this deadline'))
#
#         column_ids = [item['statement_column'] for item in report_items]
#         statement_columns = StatementColumn.objects.select_related('parent').in_bulk(column_ids)
#
#         if len(statement_columns) != len(set(column_ids)):
#             raise CustomExceptionError(400, _('Invalid statement column(s) found.'))
#
#         organization_ids = set()
#         plan_column_ids = []
#         plan_values = {}
#
#         plant_ilova_titles = {"ko‘chat", "nihol", "ko‘chat ва ниҳол"}
#         any_plant_based = False
#
#         for item in report_items:
#             col_id = item['statement_column']
#             value = item['value']
#             column = statement_columns.get(col_id)
#             root = get_root_column(column)
#             is_plant_based = root.title.strip().lower() in plant_ilova_titles
#
#             if is_plant_based:
#                 any_plant_based = True
#                 if not isinstance(value, list):
#                     raise CustomExceptionError(400, _('Value must be a list for plant-based reports.'))
#                 for entry in value:
#                     if 'plant_id' not in entry or 'value' not in entry:
#                         raise CustomExceptionError(400, _('Each plant entry must contain plant_id and value.'))
#                     try:
#                         float(entry['value'])
#                     except (ValueError, TypeError):
#                         raise CustomExceptionError(400, _('Plant value must be numeric.'))
#             else:
#                 if column.is_organization:
#                     org_id = self.validate_uuid(value)
#                     organization_ids.add(org_id)
#                 elif column.status_plan is not None:
#                     try:
#                         plan_values[col_id] = int(value)
#                     except ValueError:
#                         raise CustomExceptionError(400, _('Plan value must be an integer.'))
#                     plan_column_ids.append(col_id)
#
#         if not any_plant_based:
#             if len(organization_ids) != 1:
#                 raise CustomExceptionError(400, _('Invalid organizations. Multiple different organizations found.'))
#
#             organization_id = organization_ids.pop()
#             if not Organization.objects.filter(id=organization_id).exists() or organization_id != user.organization.id:
#                 raise CustomExceptionError(400, _('Invalid organization.'))
#
#         # if plan_column_ids:
#         #     plans = Plan.objects.filter(column_id__in=plan_column_ids)
#         #     plans_map = {p.column_id: p for p in plans}
#         #     for col_id in plan_column_ids:
#         #         plan = plans_map.get(col_id)
#         #         if not plan or plan.plan_value != plan_values[col_id]:
#         #             raise CustomExceptionError(400, _('Invalid Plan value'))
#
#         if not any_plant_based:
#             cache.set(self.CACHE_KEY, organization_id)
#
#         today = date.today()
#         submit_at = deadline.submit_at
#
#         def get_week_of_month(day):
#             first_day = day.replace(day=1)
#             adjusted_dom = day.day + first_day.weekday()
#             return (adjusted_dom - 1) // 7 + 1
#
#         if statement.period == PeriodChoices.KUNLIK:
#             report_day = date.fromisoformat(submit_at)
#             if report_day >= today:
#                 raise CustomExceptionError(400, {'submit_at': _('You can only submit for past days.')})
#         elif statement.period == PeriodChoices.HAFTALIK:
#             try:
#                 year, month, week_str = submit_at.split('-')
#                 year = int(year)
#                 month = int(month)
#                 week = int(week_str.lstrip('W'))
#             except (ValueError, AttributeError):
#                 raise CustomExceptionError(400, {'submit_at': _('Invalid weekly format. Must be YYYY-MM-Wn')})
#
#             if year > today.year or (year == today.year and month > today.month):
#                 raise CustomExceptionError(400, {'submit_at': _('You can only submit for past weeks.')})
#             if year == today.year and month == today.month and week >= get_week_of_month(today):
#                 raise CustomExceptionError(400, {'submit_at': ['You can only submit for past weeks.']})
#         elif statement.period == PeriodChoices.OYLIK:
#             year, month = map(int, submit_at.split('-'))
#             if year > today.year or (year == today.year and month >= today.month):
#                 raise CustomExceptionError(400, {'submit_at': _('You can only submit for past months.')})
#         elif statement.period == PeriodChoices.CHORAKLIK:
#             year, quarter = int(submit_at[:4]), int(submit_at[-1])
#             current_quarter = (today.month - 1) // 3 + 1
#             if year > today.year or (year == today.year and quarter >= current_quarter):
#                 raise CustomExceptionError(400, {'submit_at': _('You can only submit for past quarters.')})
#         elif statement.period == PeriodChoices.YILLIK:
#             year = int(submit_at)
#             if year >= today.year:
#                 raise CustomExceptionError(400, {'submit_at': _('You can only submit for past years.')})
#
#         if Report.objects.filter(organization_id=user.organization.id, statement=statement, deadline=deadline).exists():
#             raise CustomExceptionError(400, {'report': _('This report already exists.')})
#
#         return attrs
#
#     def create(self, validated_data):
#         items_data = validated_data.pop('report_items')
#         deadline = validated_data['deadline']
#         validated_data['statement'] = deadline.statement
#         user = self.context['request'].user
#
#         organization_id = cache.get(self.CACHE_KEY)
#         organization = Organization.objects.get(id=organization_id) if organization_id else self.context['request'].user.organization
#         validated_data['organization'] = organization
#         cache.delete(self.CACHE_KEY)
#
#         column_ids = [item['statement_column'] for item in items_data]
#         statement_columns = StatementColumn.objects.in_bulk(column_ids)
#
#         with transaction.atomic():
#             report = Report.objects.create(**validated_data)
#
#             for item in items_data:
#                 col_id = item['statement_column']
#                 column = statement_columns[col_id]
#                 value = item['value']
#
#                 root = get_root_column(column)
#                 is_plant_based = root.title.strip().lower() in {"ko‘chat", "nihol", "ko‘chat ва ниҳол"}
#
#                 if is_plant_based:
#                     process_plant_values(report=report, statement_column=column, plant_value_list=value)
#                 else:
#                     ReportItem.objects.create(
#                         report=report,
#                         statement_column=column,
#                         value=value
#                     )
#
#             user = self.context['request'].user
#             report.created_by= user
#             report.save()
#
#         return report
