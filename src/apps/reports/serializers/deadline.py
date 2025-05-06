from rest_framework import serializers
from apps.general.models import Organization
from apps.reports.models import Deadline, Statement
from apps.reports.serializers.statement import StatementSerializer


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('id', 'name')


class StatementLightSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = Statement
        fields = ("id", "name", "period", "parent_name")

class DeadlineSerializer(serializers.ModelSerializer):
    organizations = OrganizationSerializer(many=True, read_only=True)
    statement = StatementLightSerializer(read_only=True)

    class Meta:
        model = Deadline
        fields = ("id", "organizations", "statement", "submit_at")

