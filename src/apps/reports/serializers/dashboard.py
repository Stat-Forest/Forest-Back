from rest_framework import serializers

from apps.reports.models import DashboardStat


class DashboardStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardStat
        fields = [
            'sent_reports', 'returned_reports', 'accepted_reports',
            'draft_reports', 'responsible_users', 'deadlines',
        ]
