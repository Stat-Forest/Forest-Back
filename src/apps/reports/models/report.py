from django.db import models
from django.conf import settings
from django.db.models import Q
from django.db.models import TextChoices
from django.db.models.constraints import UniqueConstraint

from django.utils.timezone import  timezone
from django.utils.translation import gettext_lazy as _

from apps.reports.choices import UserRoleChoices
from apps.utils.services import RegionChoices
from apps.base.models import AbstractBaseModel


class Report(AbstractBaseModel):
    class StatusChoices(models.TextChoices):
        SAVED = 'saved', _('Saved')
        SENT = 'sent', _('Sent')
        CANCELLED = 'cancelled', _('Cancelled')
        ACCEPTED = 'accepted', _('Accepted')

    class TimeStatus(models.TextChoices):
        ON_TIME = 'on_time', _('Bajarilgan')
        LATE = 'late', _('Kechiktirilgan')

    class ReportSeasonChoices(TextChoices):
        SPRING = 'spring', 'Bahorgi'
        AUTUMN = 'autumn', 'Kuzgi'


    republic = models.ForeignKey(
      "general.Republic",
      on_delete=models.PROTECT,
      related_name="reports",
      blank=True,
      null=True
    )

    organization = models.ForeignKey(
        "general.Organization",
        on_delete=models.PROTECT,
        verbose_name=_("Organization"),
        related_name="reports",
        db_index=True,
        blank=True,
        null=True
    )
    statement = models.ForeignKey(
        "reports.Statement",
        on_delete=models.PROTECT,
        verbose_name=_("Statement"),
        related_name="reports",
    )
    deadline = models.ForeignKey(
        "reports.Deadline",
        on_delete=models.PROTECT,
        verbose_name=_("Deadline"),
        related_name="reports",
    )
    source_report = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )

    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.SAVED,
        verbose_name=_("Status"),
        db_index=True
    )
    cancel_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Cancel reason"),
        help_text=_("Reason for cancelling the report")
    )
    sent_at = models.DateTimeField(
        blank=True,
        null=True,
    )
    cancelled_at = models.DateTimeField(
        blank=True,
        null=True,
    )
    accepted_at = models.DateTimeField(
        blank=True,
        null=True,
    )
    sent_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False,
        related_name="reports_sent_by",
    )
    sent_by_org = models.ForeignKey(
        "general.Organization",
        on_delete=models.PROTECT,
        verbose_name=_("Organization"),
        related_name="sent_by_reports",
        db_index=True,
        null=True,
        blank=True,
    )
    sent_by_role = models.CharField(
        choices=UserRoleChoices.choices,
        max_length=50,
        null=True,
        blank=True,
    )
    is_general = models.BooleanField(
      default=False, db_index=True
    )

    is_individual_general = models.BooleanField(
        default=False
    )

    is_report = models.BooleanField(
        default=True,
        db_index=True
    )

    is_republic = models.BooleanField(
        default=False
    )

    is_plant_based = models.BooleanField(
        default=False,
        help_text="This field for reports with creating plants"
    )

    region = models.CharField(
      max_length=50,
      choices=RegionChoices.choices,
      null=True,
      blank=True,
      db_index=True,
      help_text="Viloyatni to‘g‘ridan-to‘g‘ri bog‘lash uchun"
    )
    time_status = models.CharField(
        max_length=20,
        choices=TimeStatus.choices,
        blank=True,
        null=True
    )
    report_season = models.CharField(
        max_length=10,
        choices=ReportSeasonChoices.choices,
        blank=True,
        null=True
    )

    foot_note = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Foydalanuvchi tomonidan kiritilgan izoh")
    )

    # def __str__(self):
    #     return f"{self.organization.name} "

    def cancel(self, reason: str):
      if not reason:
        raise ValueError("Reason must be required.")

      prev = self.status
      self.status = Report.StatusChoices.CANCELLED
      self.cancel_reason = reason
      self.cancelled_at = timezone.now()
      self.save(update_fields=["status", "cancel_reason", "cancelled_at"])

      if prev == Report.StatusChoices.ACCEPTED:
        from apps.reports.services.general_report import aggregate_general_report
        aggregate_general_report(statement=self.statement, deadline=self.deadline)

    class Meta:
        verbose_name = "Hisobot"
        verbose_name_plural = "Hisobotlar"
        ordering = ['-created_at']
        constraints = [
            UniqueConstraint(
                fields=["organization", "statement", "deadline","report_season"],
                condition=Q(is_individual_general=False),
                name="unique_org_statement_deadline_only_for_non_individual_general"
            )
        ]
        indexes = [
            models.Index(fields=['organization', 'statement', 'status', '-created_at']),
            models.Index(fields=['statement', 'status']),
            models.Index(fields=['organization', 'status']),
        ]