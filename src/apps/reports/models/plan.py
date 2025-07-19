from django.db import models
from django.core.validators import MinValueValidator

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.base.models import AbstractBaseModel


class Plan(AbstractBaseModel):
    statement = models.ForeignKey(
        'reports.Statement',
        on_delete=models.CASCADE,
    )
    organization = models.ForeignKey(
        'general.Organization',
        on_delete=models.CASCADE
    )
    year = models.PositiveIntegerField(
        validators=[MinValueValidator(1900)]
    )

    class Meta:
        ordering = ('year',)
        unique_together = (
            'statement','organization','year'
            )


class PlanItem(AbstractBaseModel):
    plan = models.ForeignKey(
        'reports.Plan',
        on_delete=models.CASCADE,
        related_name='plan_items'
    )
    column = models.ForeignKey(
        'reports.StatementColumn',
        on_delete=models.CASCADE,
        related_name='plans',

    )
    plan_value = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('column',)
        unique_together = (
            'column', 'plan'
        )
