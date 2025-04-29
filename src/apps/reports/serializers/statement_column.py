from rest_framework import serializers

from apps.reports.models import StatementColumn


class StatementColumnListSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatementColumn
        fields = ['id', 'title', 'ordering', 'statement']
