from rest_framework import serializers
from apps.reports.models import Plan
from apps.reports.serializers import StatementColumnTreeSerializer


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ['organization', 'column', 'year', 'plan_value']
