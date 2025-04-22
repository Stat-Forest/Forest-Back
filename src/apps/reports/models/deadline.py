from django.db import models

from apps.base.models import AbstractBaseModel
from apps.general.models import Organization
from apps.utils.services import StatementChoices, PeriodChoices


class Deadline(AbstractBaseModel):
    organization = models.ManyToManyField(Organization)
    statement = models.CharField(max_length=255,choices=StatementChoices.choices)
    period = models.CharField(max_length=10, choices=PeriodChoices.choices)
    submit_at = models.DateTimeField()

    def __str__(self):
        return f'Statement {self.statement} -Submit at {self.submit_at}'