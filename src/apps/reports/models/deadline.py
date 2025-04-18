from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models import AbstractBaseModel
from apps.general.models import Organization
from apps.utils.services import StatementChoices, PeriodChoices


class Deadline(AbstractBaseModel):
    organization = models.ManyToManyField(
        Organization,
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
    submission_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _('Deadline')
        verbose_name_plural = _('Deadline')

    def __str__(self):
        return self.statement
