from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.base.models import AbstractBaseModel


class Plan(AbstractBaseModel):
    organization = models.ForeignKey(
        'general.Organization',
        on_delete=models.CASCADE
    )
    column = models.ForeignKey(
        'reports.StatementColumn',
        on_delete=models.CASCADE,
        related_name='plans',

    )
    year = models.PositiveIntegerField(
        validators=[MinValueValidator(1900)]
    )
    plan_value = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('year',)
        unique_together = ('organization', 'column') 