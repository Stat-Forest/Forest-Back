from rest_framework import serializers

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Plan

class PlanSerializer(serializers.ModelSerializer):
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
        from django.utils import timezone

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


class PlanListSerializer(serializers.ModelSerializer):
    statement_name = serializers.CharField(source='statement.name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    column_title = serializers.CharField(source='column.title', read_only=True)

    class Meta:
        model = Plan
        fields = [
            'id',
            'statement',
            'statement_name',
            'organization',
            'organization_name',
            'column',
            'column_title',
            'year',
            'plan_value'
        ]