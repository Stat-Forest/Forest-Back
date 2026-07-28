# from django.core.exceptions import ValidationError
# from django.utils import timezone
# from django.utils.translation import gettext_lazy as _
# from rest_framework import serializers
#
# from apps.reports.models import Report
# from apps.base.serializers import CustomModelSerializer
# from apps.reports.services.general_report import aggregate_general_report
# from apps.reports.services.quarter_validator import DaromadQuarterService
#
#
# class ReportCancelSerializer(CustomModelSerializer):
#     id = serializers.UUIDField(write_only=True, required=True)
#     cancel_reason = serializers.CharField(write_only=True, required=True)
#
#     class Meta:
#         model = Report
#         fields = ["id", "status", "cancel_reason", "cancelled_at"]
#         read_only_fields = ["status", "cancelled_at"]
#
#     def validate(self, attrs):
#         instance: Report = self.instance
#
#         if instance.status == Report.StatusChoices.CANCELLED:
#             raise ValidationError(_("Report already cancelled."))
#
#         if not attrs.get("cancel_reason"):
#             raise ValidationError(_("Cancel reason is required when cancelling a report."))
#
#         return attrs
#
#     def save(self, **kwargs):
#         instance: Report = self.instance
#         previous_status = instance.status
#
#         instance.status = Report.StatusChoices.CANCELLED
#         instance.cancel_reason = self.validated_data["cancel_reason"]
#         instance.cancelled_at = timezone.now()
#
#         update_fields = ["status", "cancel_reason", "cancelled_at"]
#
#         if DaromadQuarterService.is_daromad_report(instance) and instance.current_quarter:
#             status_field = DaromadQuarterService.get_quarter_status_field(instance.current_quarter)
#             setattr(instance, status_field, Report.StatusChoices.CANCELLED)
#             DaromadQuarterService.mark_quarter_cancelled(instance, instance.current_quarter)
#             update_fields.extend([status_field, "quarter_status_dates"])
#
#         instance.save(update_fields=list(dict.fromkeys(update_fields)))
#
#         if previous_status == Report.StatusChoices.ACCEPTED:
#             aggregate_general_report(
#                 instance.statement,
#                 instance.deadline,
#                 instance.organization.region
#             )
#
#         return instance