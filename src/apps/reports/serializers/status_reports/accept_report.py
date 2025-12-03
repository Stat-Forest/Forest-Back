from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Report
from apps.reports.services.general_report import aggregate_general_report


class ReportAcceptSerializer(serializers.Serializer):
    id = serializers.UUIDField(write_only=True, required=True)
    status = serializers.CharField(read_only=True)
    accepted_at = serializers.DateTimeField(read_only=True)

    def validate(self, attrs):
        instance: Report = self.context["report_instance"]
        if instance.status != Report.StatusChoices.SENT:
            raise CustomExceptionError(
                code=400,
                detail=_("Report must be in SENT state to be accepted.")
            )
        return attrs

    def save(self, **kwargs):
        instance: Report = self.context["report_instance"]

        # 1) STATUS → ACCEPTED
        instance.status = Report.StatusChoices.ACCEPTED
        instance.accepted_at = timezone.now()

        # 2) TIME STATUS LOGIC
        deadline = instance.deadline
        if deadline and deadline.deadline_at:
            report_date = instance.created_at.date()
            deadline_date = deadline.deadline_at

            if report_date <= deadline_date:
                instance.time_status = Report.TimeStatus.ON_TIME
            else:
                instance.time_status = Report.TimeStatus.LATE

        # 3) SAQLASH
        instance.save(update_fields=["status", "accepted_at", "time_status"])

        # 4) GENERAL REPORT AGGREGATION
        aggregate_general_report(
            instance.statement,
            instance.deadline,
            instance.organization.region
        )

        return instance
