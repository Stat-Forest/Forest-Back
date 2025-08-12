from django.core.exceptions import ValidationError
from django.utils import timezone

from django.utils.translation import gettext_lazy as _

from apps.reports.models import Report
from apps.base.serializers import CustomModelSerializer
from apps.reports.services.general_report import aggregate_general_report


class ReportCancelSerializer(CustomModelSerializer):
    class Meta:
        model = Report
        fields = ["id", "status", "cancel_reason", "cancelled_at"]

    def validate(self, attrs):
        instance: Report = self.instance
        new_status = attrs.get("status", instance.status)

        if new_status != Report.StatusChoices.CANCELLED:
            raise ValidationError("Cancel endpoint only allows transitioning to cancelled.")

        if not attrs.get("cancel_reason"):
            raise ValidationError(_("Cancel reason is required when cancelling an accepted report."))

        return attrs

    def save(self, **kwargs):
        instance: Report = self.instance
        previous_status = instance.status
        instance = super().save(**kwargs)

        if previous_status == Report.StatusChoices.ACCEPTED and instance.status == Report.StatusChoices.CANCELLED:
            aggregate_general_report(instance.statement, instance.deadline)

        if instance.status == Report.StatusChoices.CANCELLED and not instance.cancelled_at:
            instance.cancelled_at = timezone.now()
            instance.save(update_fields=["cancelled_at"])

        return instance