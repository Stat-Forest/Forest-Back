from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models import AbstractBaseModel
from apps.utils.services import StatementChoices


class Report(AbstractBaseModel):
    class StatusChoices(models.TextChoices):
        NEW = 'new', _('New')
        SENT = 'sent', _('Sent')
        CANCELLED = 'cancelled', _('Cancelled')
        EXCEPTED = 'excepted', _('Excepted')

    organization = models.ForeignKey(
        "general.Organization",
        on_delete=models.PROTECT,
        verbose_name=_("Organization"),
        related_name="reports",
        db_index=True
    )
    statement = models.CharField(
        max_length=255,
        choices=StatementChoices.choices,
        verbose_name=_("Statement"),
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.NEW,
        verbose_name=_("Status"),
        db_index=True
    )

    def __str__(self):
        return f"{self.organization.title} - {self.get_statement_display()} [{self.get_status_display()}]"

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["organization", "statement"]),
            models.Index(fields=["status"]),
        ]
