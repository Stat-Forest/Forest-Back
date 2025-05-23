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


class ReportItemCreateSerializer(serializers.Serializer):
    statement_column = serializers.UUIDField()
    value = serializers.CharField()


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

        column_ids = [item['statement_column'] for item in report_items]
        statement_columns = StatementColumn.objects.in_bulk(column_ids)
        if len(statement_columns) != len(set(column_ids)):
            raise CustomExceptionError(400, _('Invalid statement column(s) found.'))

        organization_ids = set()
        plan_column_ids = []
        plan_values = {}

        for item in report_items:
            col_id = item['statement_column']
            value = item['value']
            column = statement_columns.get(col_id)

            if column.is_organization:
                org_id = self.validate_uuid(value)
                organization_ids.add(org_id)

            elif column.status_plan is not None:
                try:
                    plan_values[col_id] = int(value)
                except ValueError:
                    raise CustomExceptionError(400, _('Plan value must be an integer.'))
                plan_column_ids.append(col_id)

            else:
                try:
                    float(value)
                except (ValueError, TypeError):
                    raise CustomExceptionError(400, _('Value must be a number.'))

        if len(organization_ids) != 1:
            raise CustomExceptionError(400, _('Invalid organizations. Multiple different organizations found.'))

        organization_id = organization_ids.pop()
        if not Organization.objects.filter(id=organization_id).exists():
            raise CustomExceptionError(400, _('Invalid organization.'))

        # Optimize plan check
        if plan_column_ids:
            plans = Plan.objects.filter(column_id__in=plan_column_ids)
            plans_map = {p.column_id: p for p in plans}
            for col_id in plan_column_ids:
                plan = plans_map.get(col_id)
                if not plan or plan.plan_value != plan_values[col_id]:
                    raise CustomExceptionError(400, _('Invalid Plan value'))

        cache.set(self.CACHE_KEY, organization_id)

        # Period checks (only allow past periods)
        today = date.today()
        submit_at = deadline.submit_at

        def get_week_of_month(day):
            first_day = day.replace(day=1)
            adjusted_dom = day.day + first_day.weekday()
            return (adjusted_dom - 1) // 7 + 1

        if statement.period == PeriodChoices.KUNLIK:
            # Format: YYYY-MM-DD
            report_day = date.fromisoformat(submit_at)
            if report_day >= today:
                raise CustomExceptionError(400, {'submit_at': ['You can only submit for past days.']})

        elif statement.period == PeriodChoices.HAFTALIK:
            # Format: YYYY-MM-X
            year, month, week = map(int, submit_at.split('-'))
            if year > today.year or (year == today.year and month > today.month):
                raise CustomExceptionError(400, {'submit_at': ['You can only submit for past weeks.']})
            if year == today.year and month == today.month and week >= get_week_of_month(today):
                raise CustomExceptionError(400, {'submit_at': ['You can only submit for past weeks.']})

        elif statement.period == PeriodChoices.OYLIK:
            # Format: YYYY-MM
            year, month = map(int, submit_at.split('-'))
            if year > today.year or (year == today.year and month >= today.month):
                raise CustomExceptionError(400, {'submit_at': ['You can only submit for past months.']})

        elif statement.period == PeriodChoices.CHORAKLIK:
            # Format: YYYY-QX
            year, quarter = int(submit_at[:4]), int(submit_at[-1])
            current_quarter = (today.month - 1) // 3 + 1
            if year > today.year or (year == today.year and quarter >= current_quarter):
                raise CustomExceptionError(400, {'submit_at': ['You can only submit for past quarters.']})

        elif statement.period == PeriodChoices.YILLIK:
            # Format: YYYY
            year = int(submit_at)
            if year >= today.year:
                raise CustomExceptionError(400, {'submit_at': ['You can only submit for past years.']})

        # Check uniqueness
        if Report.objects.filter(organization_id=organization_id, statement=statement, deadline=deadline).exists():
            raise CustomExceptionError(400, {'report': ['This report already exists.']})

        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop('report_items')
        deadline = validated_data['deadline']
        validated_data['statement'] = deadline.statement

        organization_id = cache.get(self.CACHE_KEY)
        organization = Organization.objects.get(id=organization_id)
        validated_data['organization'] = organization
        cache.delete(self.CACHE_KEY)

        column_ids = [item['statement_column'] for item in items_data]
        statement_columns = StatementColumn.objects.in_bulk(column_ids)

        with transaction.atomic():
            report = Report.objects.create(**validated_data)
            report_items = [
                ReportItem(
                    report=report,
                    statement_column=statement_columns[item['statement_column']],
                    value=item['value']
                ) for item in items_data
            ]
            ReportItem.objects.bulk_create(report_items)

        return report
