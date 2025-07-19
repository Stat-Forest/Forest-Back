from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from apps.base.models import AbstractBaseModel
from apps.users.models import CustomUser


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
    sent_by_role =  models.CharField(
        choices=CustomUser.Role.choices,
        max_length=50,
        help_text="Foydalanuvchining tizimdagi roli",
        null=True,
        blank=True,
    )

    # def __str__(self):
    #     return f"{self.organization.name} "

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        ordering = ['-created_at']
        unique_together = ('organization', 'statement','deadline')

