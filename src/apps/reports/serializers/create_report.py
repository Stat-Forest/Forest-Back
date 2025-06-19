import json
from uuid import UUID
from datetime import date

from django.db import transaction
from django.core.cache import cache
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from apps.general.models import Organization
from apps.utils.services.choices import PeriodChoices
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Report, ReportItem, StatementColumn, Plan
from apps.utils.services.find_statement_column import get_root_column
from apps.utils.services.sum_parent_plant import process_plant_values


class ReportItemCreateSerializer(serializers.Serializer):
    statement_column = serializers.UUIDField()
    value = serializers.JSONField()


class ReportCreateSerializer(serializers.ModelSerializer):
    report_items = ReportItemCreateSerializer(many=True, write_only=True)
    CACHE_KEY = 'report_organization'

    class Meta:
        model = Report
        fields = ['id', 'deadline', 'report_items']

    def validate_uuid(self, value):
        try:
            return UUID(str(value))
        except ValueError:
            raise CustomExceptionError(400, _('Organization ID must be a valid UUID.'))

    def validate(self, attrs):
        report_items = attrs['report_items']
        deadline = attrs['deadline']
        statement = deadline.statement
        user = self.context['request'].user

        if not user.statement:
            raise CustomExceptionError(400, _('User must have a statement to create report !'))

        if user.statement != statement.parent:
            raise CustomExceptionError(400, _('User statement does not match deadline statement !'))

        if not deadline.organizations.filter(id=user.organization.id).exists():
            raise CustomExceptionError(400, _('User organization is not related to this deadline'))

        column_ids = [item['statement_column'] for item in report_items]
        statement_columns = StatementColumn.objects.select_related('parent').in_bulk(column_ids)

        if len(statement_columns) != len(set(column_ids)):
            raise CustomExceptionError(400, _('Invalid statement column(s) found.'))

        organization_ids = set()
        plan_column_ids = []
        plan_values = {}

        plant_ilova_titles = {"ko‘chat", "nihol", "ko‘chat ва ниҳол"}
        any_plant_based = False

        for item in report_items:
            col_id = item['statement_column']
            value = item['value']
            column = statement_columns.get(col_id)
            root = get_root_column(column)
            is_plant_based = root.title.strip().lower() in plant_ilova_titles

            if is_plant_based:
                any_plant_based = True
                if not isinstance(value, list):
                    raise CustomExceptionError(400, _('Value must be a list for plant-based reports.'))
                for entry in value:
                    if 'plant_id' not in entry or 'value' not in entry:
                        raise CustomExceptionError(400, _('Each plant entry must contain plant_id and value.'))
                    try:
                        float(entry['value'])
                    except (ValueError, TypeError):
                        raise CustomExceptionError(400, _('Plant value must be numeric.'))
            else:
                if column.is_organization:
                    org_id = self.validate_uuid(value)
                    organization_ids.add(org_id)
                elif column.status_plan is not None:
                    try:
                        plan_values[col_id] = int(value)
                    except ValueError:
                        raise CustomExceptionError(400, _('Plan value must be an integer.'))
                    plan_column_ids.append(col_id)

        if not any_plant_based:
            if len(organization_ids) != 1:
                raise CustomExceptionError(400, _('Invalid organizations. Multiple different organizations found.'))

            organization_id = organization_ids.pop()
            if not Organization.objects.filter(id=organization_id).exists() or organization_id != user.organization.id:
                raise CustomExceptionError(400, _('Invalid organization.'))

        if plan_column_ids:
            plans = Plan.objects.filter(column_id__in=plan_column_ids)
            plans_map = {p.column_id: p for p in plans}
            for col_id in plan_column_ids:
                plan = plans_map.get(col_id)
                if not plan or plan.plan_value != plan_values[col_id]:
                    raise CustomExceptionError(400, _('Invalid Plan value'))

        if not any_plant_based:
            cache.set(self.CACHE_KEY, organization_id)

        today = date.today()
        submit_at = deadline.submit_at

        def get_week_of_month(day):
            first_day = day.replace(day=1)
            adjusted_dom = day.day + first_day.weekday()
            return (adjusted_dom - 1) // 7 + 1

        if statement.period == PeriodChoices.KUNLIK:
            report_day = date.fromisoformat(submit_at)
            if report_day >= today:
                raise CustomExceptionError(400, {'submit_at': ['You can only submit for past days.']})
        elif statement.period == PeriodChoices.HAFTALIK:
            year, month, week = map(int, submit_at.split('-'))
            if year > today.year or (year == today.year and month > today.month):
                raise CustomExceptionError(400, {'submit_at': ['You can only submit for past weeks.']})
            if year == today.year and month == today.month and week >= get_week_of_month(today):
                raise CustomExceptionError(400, {'submit_at': ['You can only submit for past weeks.']})
        elif statement.period == PeriodChoices.OYLIK:
            year, month = map(int, submit_at.split('-'))
            if year > today.year or (year == today.year and month >= today.month):
                raise CustomExceptionError(400, {'submit_at': ['You can only submit for past months.']})
        elif statement.period == PeriodChoices.CHORAKLIK:
            year, quarter = int(submit_at[:4]), int(submit_at[-1])
            current_quarter = (today.month - 1) // 3 + 1
            if year > today.year or (year == today.year and quarter >= current_quarter):
                raise CustomExceptionError(400, {'submit_at': ['You can only submit for past quarters.']})
        elif statement.period == PeriodChoices.YILLIK:
            year = int(submit_at)
            if year >= today.year:
                raise CustomExceptionError(400, {'submit_at': ['You can only submit for past years.']})

        if Report.objects.filter(organization_id=user.organization.id, statement=statement, deadline=deadline).exists():
            raise CustomExceptionError(400, {'report': ['This report already exists.']})

        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop('report_items')
        deadline = validated_data['deadline']
        validated_data['statement'] = deadline.statement

        organization_id = cache.get(self.CACHE_KEY)
        organization = Organization.objects.get(id=organization_id) if organization_id else self.context[
            'request'].user.organization
        validated_data['organization'] = organization
        cache.delete(self.CACHE_KEY)

        column_ids = [item['statement_column'] for item in items_data]
        statement_columns = StatementColumn.objects.in_bulk(column_ids)

        with transaction.atomic():
            report = Report.objects.create(**validated_data)

            for item in items_data:
                col_id = item['statement_column']
                column = statement_columns[col_id]
                value = item['value']

                root = get_root_column(column)
                is_plant_based = root.title.strip().lower() in {"ko‘chat", "nihol", "ko‘chat ва ниҳол"}

                if is_plant_based:
                    process_plant_values(report=report, statement_column=column, plant_value_list=value)
                else:
                    ReportItem.objects.create(
                        report=report,
                        statement_column=column,
                        value=value
                    )

        return report
