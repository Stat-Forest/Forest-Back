from django.db import models
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
    year = models.PositiveIntegerField()
    plan_value = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('year',)
        unique_together = ('organization', 'column')