# serializers.py
from datetime import datetime

from django.utils import timezone
from rest_framework import serializers
from apps.reports.models import Report

class ReportSendSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField()
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Report
        fields = ['id', 'status']

    def update(self, instance, validated_data):
        org_director = self.context['request'].user
        instance.status = Report.StatusChoices.SENT
        now = timezone.now().strftime('%Y-%m-%d %H:%M')
        instance.sent_at = datetime.strptime(now, '%Y-%m-%d %H:%M')
        instance.sent_by= org_director
        instance.sent_by_org = org_director.organization
        instance.sent_by_role = org_director.role
        instance.save()
        return instance
