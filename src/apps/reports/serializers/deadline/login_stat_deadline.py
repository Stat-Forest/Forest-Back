# serializers.py
from rest_framework import serializers
from apps.reports.models import Deadline, Report


class DeadlineReportListSerializer(serializers.ModelSerializer):
    statement_name = serializers.CharField(source='statement.name', read_only=True)
    statement_id = serializers.IntegerField(source='statement.id', read_only=True)
    statement_period = serializers.CharField(source='statement.period', read_only=True)
    parent_statement_name = serializers.CharField(source='statement.parent.name', read_only=True)

    total_organizations = serializers.SerializerMethodField()
    submitted_organizations = serializers.SerializerMethodField()
    pending_organizations = serializers.SerializerMethodField()
    submission_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Deadline
        fields = [
            'id',
            'statement_id',
            'statement_name',
            'parent_statement_name',
            'statement_period',
            'submit_at',
            'deadline_at',
            'total_organizations',
            'submitted_organizations',
            'pending_organizations',
            'submission_percentage',
            'created_at',
        ]

    def _get_deadlines_for_period(self, obj):
        all_deadlines = self.context.get("all_deadlines")
        if all_deadlines is not None:
            return [d for d in all_deadlines if d.submit_at == obj.submit_at]
        return [obj]

    def get_total_organizations(self, obj):
        deadlines = self._get_deadlines_for_period(obj)
        org_ids = set()
        for d in deadlines:
            for org_id in d.organizations.values_list('id', flat=True):
                org_ids.add(org_id)
        return len(org_ids)

    def get_submitted_organizations(self, obj):
        deadlines = self._get_deadlines_for_period(obj)
        return Report.objects.filter(
            deadline__in=deadlines,
            status=Report.StatusChoices.ACCEPTED,
            is_report=True,
        ).values('organization').distinct().count()

    def get_pending_organizations(self, obj):
        total = self.get_total_organizations(obj)
        submitted = self.get_submitted_organizations(obj)
        return total - submitted

    def get_submission_percentage(self, obj):
        total = self.get_total_organizations(obj)
        if total == 0:
            return 0
        submitted = self.get_submitted_organizations(obj)
        return round((submitted / total) * 100, 2)