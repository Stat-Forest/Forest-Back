from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from apps.reports.models import Report
from apps.base.serializers import CustomModelSerializer
from apps.reports.services.general_report import aggregate_general_report
from apps.reports.services.quarter_validator import DaromadQuarterService


class ReportCancelSerializer(CustomModelSerializer):
    id = serializers.UUIDField(write_only=True, required=True)
    cancel_reason = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Report
        fields = ["id", "status", "cancel_reason", "cancelled_at"]
        read_only_fields = ["status", "cancelled_at"]

    def validate(self, attrs):
        instance: Report = self.instance

        if DaromadQuarterService.is_daromad_report(instance):
            # Daromad uchun: current_quarter allaqachon CANCELLED bo'lmasligi kerak
            current_quarter = instance.current_quarter
            if current_quarter:
                current_quarter_status = instance.get_quarter_status(current_quarter)
                if current_quarter_status == Report.StatusChoices.CANCELLED:
                    raise ValidationError(
                        _(f"{DaromadQuarterService.get_quarter_display(current_quarter)} "
                          f"allaqachon bekor qilingan.")
                    )
        else:
            if instance.status == Report.StatusChoices.CANCELLED:
                raise ValidationError(_("Report already cancelled."))

        if not attrs.get("cancel_reason"):
            raise ValidationError(_("Cancel reason is required when cancelling a report."))

        return attrs

    def save(self, **kwargs):
        instance: Report = self.instance
        previous_status = instance.status

        instance.cancel_reason = self.validated_data["cancel_reason"]
        instance.cancelled_at = timezone.now()

        update_fields = ["cancel_reason", "cancelled_at"]

        if DaromadQuarterService.is_daromad_report(instance) and instance.current_quarter:
            # Daromad: faqat current_quarter ni CANCELLED qilamiz
            status_field = DaromadQuarterService.get_quarter_status_field(instance.current_quarter)
            setattr(instance, status_field, Report.StatusChoices.CANCELLED)
            DaromadQuarterService.mark_quarter_cancelled(instance, instance.current_quarter)

            # report.status = compute_report_status()
            # Agar Q1 ACCEPTED bo'lsa, cancel qilgandan keyin ham ACCEPTED qoladi
            instance.status = DaromadQuarterService.compute_report_status(instance)
            update_fields.extend([status_field, "quarter_status_dates", "status"])
        else:
            instance.status = Report.StatusChoices.CANCELLED
            update_fields.append("status")

        instance.save(update_fields=list(dict.fromkeys(update_fields)))

        # Cancel qilinganda agar oldingi holat ACCEPTED bo'lsa, general qayta hisoblanadi
        if previous_status == Report.StatusChoices.ACCEPTED:
            aggregate_general_report(
                instance.statement,
                instance.deadline,
                instance.organization.region,
            )

        return instance
