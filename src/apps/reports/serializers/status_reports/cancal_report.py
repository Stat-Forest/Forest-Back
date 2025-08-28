from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.reports.models import Report
from apps.base.serializers import CustomModelSerializer
from apps.reports.services.general_report import aggregate_general_report


class ReportCancelSerializer(CustomModelSerializer):
    id = serializers.UUIDField(write_only=True, required=True) 
    cancel_reason = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Report
        fields = ["id", "status", "cancel_reason", "cancelled_at"]
        read_only_fields = ["status", "cancelled_at"]

    def validate(self, attrs):
        instance: Report = self.instance

        # Agar report allaqachon CANCELLED bo'lsa - xato
        if instance.status == Report.StatusChoices.CANCELLED:
            raise ValidationError(_("Report already cancelled."))

        # cancel_reason majburiy (aslida required=True buni o‘zi tekshiradi)
        if not attrs.get("cancel_reason"):
            raise ValidationError(_("Cancel reason is required when cancelling a report."))

        return attrs

    def save(self, **kwargs):
        instance: Report = self.instance
        previous_status = instance.status

        # Statusni majburan CANCELLED qilish
        instance.status = Report.StatusChoices.CANCELLED
        instance.cancel_reason = self.validated_data["cancel_reason"]

        # cancelled_at har safar yangilanadi
        instance.cancelled_at = timezone.now()

        instance.save(update_fields=["status", "cancel_reason", "cancelled_at"])

        # Agar oldin ACCEPTED bo'lsa va endi CANCELLED bo'lsa - umumiy hisobotni qayta hisoblash
        if previous_status == Report.StatusChoices.ACCEPTED:
            aggregate_general_report(
                instance.statement,
                instance.deadline,
                instance.organization.region
            )

        return instance
