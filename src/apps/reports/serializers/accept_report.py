from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Report
from apps.reports.services.general_report import aggregate_general_report


class ReportAcceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["id", "status", "accepted_at"]
        read_only_fields = ["status", "accepted_at"]

    def validate(self, attrs):
        instance: Report = self.instance
        if instance.status != Report.StatusChoices.SENT:
            raise CustomExceptionError(
                code=400,
                detail=_("Report must be in SENT state to be accepted.")
            )
        return attrs

    def save(self, **kwargs):
        instance: Report = self.instance
        if instance.status == Report.StatusChoices.SENT:
            instance.status = Report.StatusChoices.ACCEPTED
            instance.accepted_at = timezone.now()
            instance.save(update_fields=["status", "accepted_at"])

            # umumiy hisobotni yangilash
            aggregate_general_report(instance.statement, instance.deadline)
        return instance
