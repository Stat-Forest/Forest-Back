from rest_framework import serializers
from apps.general.models import Organization
from apps.reports.models import Deadline
from apps.reports.serializers.statement import StatementSerializer


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('id', 'name')

class DeadlineSerializer(serializers.ModelSerializer):
    organizations = OrganizationSerializer(many=True, read_only=True)
    statement = StatementSerializer()

    class Meta:
        model = Deadline
        fields = ('id', 'organizations', 'statement', 'submit_at')
