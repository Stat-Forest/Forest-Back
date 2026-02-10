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

    def get_total_organizations(self, obj):
        """Umumiy organizatsiyalar soni"""
        return obj.organizations.count()

    def get_submitted_organizations(self, obj):
        """Hisobot yuborgan organizatsiyalar soni"""
        return Report.objects.filter(
            deadline=obj,
            status=Report.StatusChoices.ACCEPTED,
            is_report=True,
        ).values('organization').distinct().count()

    def get_pending_organizations(self, obj):
        """Hisobot yubormaganlar soni"""
        total = self.get_total_organizations(obj)
        submitted = self.get_submitted_organizations(obj)
        return total - submitted

    def get_submission_percentage(self, obj):
        """Hisobot yuborish foizi"""
        total = self.get_total_organizations(obj)
        if total == 0:
            return 0

        submitted = self.get_submitted_organizations(obj)
        return round((submitted / total) * 100, 2)