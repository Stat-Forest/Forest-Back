from django.db import models

from apps.base.models import AbstractBaseModel
from apps.utils.services import PeriodChoices


class Statement(AbstractBaseModel):
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='children',
        limit_choices_to={'parent__isnull': True},
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=100)

    period = models.CharField(
        max_length=100,
        choices=PeriodChoices.choices,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.name
