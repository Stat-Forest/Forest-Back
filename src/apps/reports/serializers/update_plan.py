from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Plan, Report, StatementColumn


class PlanUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            'id',
            'statement',
            'organization',
            'column',
            'year',
            'plan_value'
        ]

    def validate_year(self, value):
        current_year = timezone.now().year
        if value < 1900 or value > current_year:
            raise CustomExceptionError(
                400,
                {'year': ['Year must be between 1900 and current year.']}
            )
        return value

    def validate_plan_value(self, value):
        if value < 0:
            raise CustomExceptionError(
                400,
                {'plan_value': ['Plan value cannot be negative.']}
            )
        return value

    def validate(self, attrs):
        statement = attrs.get('statement', self.instance.statement if self.instance else None)
        column = attrs.get('column', self.instance.column if self.instance else None)

        if column.status_plan == StatementColumn.PlanStatus.YILLIK_TOTAL:
            raise CustomExceptionError(
                400,
                {'column': ['You cannot update TOTAL_YILLIK plan directly.']}
            )

        if statement and column:
            if column.statement != statement:
                raise CustomExceptionError(
                    400,
                    {'column': ['Column does not belong to the specified statement.']}
                )

        if self.instance:
            if Report.objects.filter(
                statement=statement,
                organization=attrs.get('organization', self.instance.organization),
                report_items__statement_column=column
            ).exists():
                raise CustomExceptionError(
                    400,
                    {'plan': ['Cannot update Plan because related Reports exist. Delete the Reports first.']}
                )

            # Check for unique constraint
            statement = attrs.get('statement', self.instance.statement)
            organization = attrs.get('organization', self.instance.organization)
            column = attrs.get('column', self.instance.column)
            year = attrs.get('year', self.instance.year)

            instance_id = self.instance.id

            conflicting_plan = Plan.objects.exclude(id=instance_id).filter(
                statement=statement,
                organization=organization,
                column=column,
                year=year
            ).first()
            if conflicting_plan:
                raise CustomExceptionError(
                    400,
                    {
                        'non_field_errors': [
                            f'The fields statement, organization, column, year must be unique together. '
                            f'A conflicting Plan exists with ID: {conflicting_plan.id}. '
                            f'Please delete or update that Plan first.'
                        ]
                    }
                )

        return attrs

    def update(self, instance, validated_data):
        with transaction.atomic():
            updated_plan = super().update(instance, validated_data)

            if updated_plan.column.status_plan == StatementColumn.PlanStatus.YILLIK:
                yillik_plans = Plan.objects.filter(
                    organization=updated_plan.organization,
                    statement=updated_plan.statement,
                    year=updated_plan.year,
                    column__status_plan=StatementColumn.PlanStatus.YILLIK
                )

                total_value = sum(p.plan_value for p in yillik_plans)

                total_column = StatementColumn.objects.filter(
                    statement=updated_plan.statement,
                    status_plan=StatementColumn.PlanStatus.YILLIK_TOTAL
                ).first()

                if total_column:
                    Plan.objects.update_or_create(
                        organization=updated_plan.organization,
                        statement=updated_plan.statement,
                        column=total_column,
                        year=updated_plan.year,
                        defaults={'plan_value': total_value}
                    )

            return updated_plan
