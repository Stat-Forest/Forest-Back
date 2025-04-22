from apps.base.serializers import CustomModelSerializer
from apps.reports.models import DashboardStat


class DashboardStatSerializer(CustomModelSerializer):
    class Meta:
        model = DashboardStat
        fields = [
            'sent_reports', 'returned_reports', 'accepted_reports',
            'draft_reports', 'responsible_users', 'deadlines',
        ]
