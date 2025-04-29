from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models import AbstractBaseModel
from apps.utils.services import  PeriodChoices


class Report(AbstractBaseModel):
    class StatusChoices(models.TextChoices):
        SAVED = 'saved', _('Saved')
        SENT = 'sent', _('Sent')
        CANCELLED = 'cancelled', _('Cancelled')
        ACCEPTED = 'accepted', _('Accepted')

    organization = models.ForeignKey(
        "general.Organization",
        on_delete=models.PROTECT,
        verbose_name=_("Organization"),
        related_name="reports",
        db_index=True
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

    def __str__(self):
        return f"{self.organization.name} "

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        ordering = ['-created_at']
        unique_together = ('organization', 'statement','deadline')