from rest_framework import serializers
from apps.reports.models import Report


class ReportListSerializer(serializers.ModelSerializer):
    period = serializers.CharField(source='statement.period')

    class Meta:
        model = Report
        fields = (
            'id', 'organization', 'statement',
            'deadline', 'period', 'status',
            'created_at','cancel_reason',
            'cancelled_at',
            'sent_at','accepted_at',
        )


