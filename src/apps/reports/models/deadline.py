from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.general.models import Organization
from apps.base.models import AbstractBaseModel
from apps.utils.services import StatementChoices, PeriodChoices


class Deadline(AbstractBaseModel):
    organizations = models.ManyToManyField(
        Organization,
        verbose_name=_("Organizations"),
        related_name="deadlines"
    )
    statement = models.CharField(
        max_length=255,
        choices=StatementChoices.choices,
        verbose_name=_("Statement"),
        db_index=True
    )
    period = models.CharField(
        max_length=10,
        choices=PeriodChoices.choices,
        verbose_name=_("Period"),
        db_index=True
    )
    submit_at = models.DateTimeField(verbose_name=_("Submission Date"))

    def __str__(self):
        return f"{self.get_statement_display()} ({self.get_period_display()}) - {self.submit_at:%Y-%m-%d %H:%M}"

    class Meta:
        verbose_name = _("Deadline")
        verbose_name_plural = _("Deadlines")
        ordering = ['-submit_at']
        unique_together = ('statement', 'period')
