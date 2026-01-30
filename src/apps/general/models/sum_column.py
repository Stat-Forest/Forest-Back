from django.db import models
from apps.base.models import AbstractBaseModel


class SumColumn(AbstractBaseModel):
    statement = models.ForeignKey(
        'reports.Statement',
        on_delete=models.CASCADE,
        related_name='sum_columns',
        blank=True,
        null=True,
        limit_choices_to={'parent__isnull': False},
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='children',
        limit_choices_to={'parent__isnull': True},
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=100)
    ordering = models.CharField(
        default="0",
        max_length=100,
        verbose_name="Ordering"
    )

    def __str__(self):
            return self.title
