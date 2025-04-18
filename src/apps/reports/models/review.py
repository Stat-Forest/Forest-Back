from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models import AbstractBaseModel
from apps.utils.services import StatementChoices, PeriodChoices, ReportType


class Review(AbstractBaseModel):
    staff_report = models.ForeignKey(
        'human_resources.StaffReport',
        on_delete=models.PROTECT
    )
    organization = models.CharField(max_length=255)
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
    class Meta:
        verbose_name = _('Review')
        verbose_name_plural = _('Reviews')

    def __str__(self):
        return self.statement
