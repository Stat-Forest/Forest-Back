from datetime import datetime

from django.utils import timezone
from rest_framework import serializers

from apps.reports.models import Report

class ReportAcceptSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField()
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Report
        fields = ['id', 'status']

    def update(self, instance, validated_data):
        instance.status = Report.StatusChoices.ACCEPTED
        now = timezone.now().strftime('%Y-%m-%d %H:%M')
        instance.accepted_at= datetime.strptime(now, '%Y-%m-%d %H:%M')
        instance.save()
        return instance
