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
        limit_choices_to={'is_plan': True}
    )
    year = models.PositiveIntegerField(
        validators=[MinValueValidator(1900)]
    )
    plan_value = models.PositiveIntegerField(default=0)

    def clean(self):
        super().clean()
        current_year = timezone.now().year

        if self.year < 1900 or self.year > current_year:
            raise CustomExceptionError(
                400,
                {'year': ['Year cannot be less than 1900.']}
            )
        if self.plan_value < 0:
            raise CustomExceptionError(
                400,
                {'plan_value': ['Plan value cannot be negative.']}
            )

    class Meta:
        ordering = ('year',)
        unique_together = ('organization', 'column')