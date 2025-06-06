from rest_framework import serializers
from django.utils import timezone
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Plan, Report

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

        if self.instance:
            statement = attrs.get('statement', self.instance.statement)
            organization = attrs.get('organization', self.instance.organization)
            column = attrs.get('column', self.instance.column)
            year = attrs.get('year', self.instance.year)

            instance_id = self.instance.id if self.instance else None

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
