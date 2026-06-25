from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Report
from apps.reports.services.general_report import aggregate_general_report
from apps.reports.services.quarter_validator import DaromadQuarterService


class ReportAcceptSerializer(serializers.Serializer):
    id = serializers.UUIDField(write_only=True, required=True)
    status = serializers.CharField(read_only=True)
    accepted_at = serializers.DateTimeField(read_only=True)

    def validate(self, attrs):
        instance: Report = self.context["report_instance"]

        if DaromadQuarterService.is_daromad_report(instance):
            # Daromad uchun: current_quarter ning statusini tekshiramiz
            current_quarter = instance.current_quarter
            if not current_quarter:
                raise CustomExceptionError(
                    code=400,
                    detail=_("Daromad hisobotida joriy chorak aniqlanmagan.")
                )

            current_quarter_status = instance.get_quarter_status(current_quarter)
            if current_quarter_status != Report.StatusChoices.SENT:
                raise CustomExceptionError(
                    code=400,
                    detail=_(
                        f"{DaromadQuarterService.get_quarter_display(current_quarter)} "
                        f"qabul qilish uchun SENT holatda bo'lishi kerak. "
                        f"Hozirgi holat: {current_quarter_status}"
                    )
                )
        else:
            # Oddiy report
            if instance.status != Report.StatusChoices.SENT:
                raise CustomExceptionError(
                    code=400,
                    detail=_("Report must be in SENT state to be accepted.")
                )

        return attrs

    def save(self, **kwargs):
        instance: Report = self.context["report_instance"]
        instance.accepted_at = timezone.now()

        # Time status
        deadline = instance.deadline
        if deadline and deadline.deadline_at:
            report_date = instance.created_at.date()
            deadline_date = deadline.deadline_at
            instance.time_status = (
                Report.TimeStatus.ON_TIME
                if report_date <= deadline_date
                else Report.TimeStatus.LATE
            )

        update_fields = ["accepted_at", "time_status"]

        if DaromadQuarterService.is_daromad_report(instance) and instance.current_quarter:
            # Daromad: faqat current_quarter statusini ACCEPTED qilamiz
            status_field = DaromadQuarterService.get_quarter_status_field(instance.current_quarter)
            setattr(instance, status_field, Report.StatusChoices.ACCEPTED)
            DaromadQuarterService.mark_quarter_accepted(instance, instance.current_quarter)

            # report.status = compute_report_status()
            # Kamida bitta ACCEPTED → ACCEPTED (bu yerda current_quarter ham ACCEPTED bo'ldi)
            instance.status = DaromadQuarterService.compute_report_status(instance)
            update_fields.extend([status_field, "quarter_status_dates", "status"])
        else:
            instance.status = Report.StatusChoices.ACCEPTED
            update_fields.append("status")

        instance.save(update_fields=list(dict.fromkeys(update_fields)))

        # aggregate_general_report(
        #     instance.statement,
        #     instance.deadline,
        #     instance.organization.region,
        # )

        return instance
