from datetime import datetime
from django.utils import timezone

from rest_framework import serializers

from apps.reports.models import Report


class ReportCancelSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField()
    cancel_reason = serializers.CharField(write_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Report
        fields = ['id', 'status', 'cancel_reason']

    def update(self, instance, validated_data):
        cancel_reason = validated_data.pop('cancel_reason')
        instance.status = Report.StatusChoices.CANCELLED
        instance.cancel_reason = cancel_reason

        now = timezone.now().strftime('%Y-%m-%d %H:%M')
        instance.cancelled_at = datetime.strptime(now, '%Y-%m-%d %H:%M')

        instance.save()
        return instance

