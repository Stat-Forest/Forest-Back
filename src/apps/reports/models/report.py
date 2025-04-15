from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models import AbstractBaseModel
from apps.general.models import Organization
from apps.utils.services import StatementChoices, PeriodChoices, ReportType


class Report(AbstractBaseModel):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    statement = models.CharField(
        max_length=10,
        choices=StatementChoices.choices
    )
    period = models.CharField(
        max_length=10,
        choices=PeriodChoices.choices
    )
    status = models.CharField(
        max_length=10,
        choices=ReportType.choices,
        default=ReportType.UNSAVED
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True
    )
    submission_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _('Report')
        verbose_name_plural = _('Reports')

    def __str__(self):
        return f"{self.organization.name} - {self.statement} "
