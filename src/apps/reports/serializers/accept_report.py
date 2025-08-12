from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.base.serializers import CustomModelSerializer
from apps.reports.models import Report
from apps.reports.services.general_report import aggregate_general_report


class ReportAcceptSerializer(CustomModelSerializer):
    class Meta:
        model = Report
        fields = ["id", "status", "accepted_at", "cancel_reason"]

    def validate(self, attrs):
        instance: Report = self.instance
        new_status = attrs.get("status", instance.status)
        if new_status != Report.StatusChoices.ACCEPTED:
            raise CustomExceptionError(code=400, detail=_("Accept endpoint only allows transitioning to accepted."))
        if instance.status != Report.StatusChoices.SENT:
            raise CustomExceptionError(code=400, detail=_("Report must be in SENT state to be accepted."))
        return attrs

    def save(self, **kwargs):
        instance: Report = self.instance
        previous_status = instance.status
        instance = super().save(**kwargs)

        if previous_status != Report.StatusChoices.ACCEPTED and instance.status == Report.StatusChoices.ACCEPTED:
            if not instance.accepted_at:
                instance.accepted_at = timezone.now()
                instance.save(update_fields=["accepted_at"])
            aggregate_general_report(instance.statement, instance.deadline)

        return instance
