from rest_framework import serializers

from apps.base.serializers import CustomModelSerializer
from apps.reports.models import Plan


class PlanDeleteSerializer(CustomModelSerializer):
    statement_name = serializers.CharField(source="statement.name")
    organization_name = serializers.CharField(source="organization.name")
    column_name = serializers.CharField(source="column.parent.title")

    class Meta:
        model = Plan
        fields = [
            "id",
            "statement",
            "statement_name",
            "organization",
            "organization_name",
            "column",
            "column_name",
            "year",
            "plan_value",
        ]
        read_only_fields = fields