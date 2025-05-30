from rest_framework import serializers
from apps.reports.models import Report,ReportItem
from apps.reports.serializers import ReportItemSerializer


class ReportListSerializer(serializers.ModelSerializer):
    period = serializers.CharField(source='statement.period')
    report_items = ReportItemSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = (
            'id', 'organization', 'statement',
            'deadline', 'period', 'status',
            'created_at', 'cancel_reason',
            'cancelled_at', 'sent_at', 'accepted_at',
            'report_items'
        )


