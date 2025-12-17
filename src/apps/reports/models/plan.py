from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import TextChoices

from apps.base.models import AbstractBaseModel



class Plan(AbstractBaseModel):

    class SeasonChoices(TextChoices):
        SPRING = 'spring', 'Bahorgi'
        AUTUMN = 'autumn', 'Kuzgi'

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
    season = models.CharField(
        max_length=10,
        choices=SeasonChoices.choices,
        blank=True,
        null=True
    )

    class Meta:
        ordering = ('year',)
        unique_together = (
            'statement', 'organization', 'year', 'season'
        )

    def __str__(self):
        return (
            f"{self.organization.name_uz} - "
            f"{self.statement.name_uz} "
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

    plan_value = models.DecimalField(
        max_digits=30,
        decimal_places=2,
        default=Decimal("0.0")
    )

    class Meta:
        ordering = ('column',)
        unique_together = (
            'column', 'plan'
        )

    def __str__(self):
        return f"{self.plan.id} | {self.column.title_uz}: {self.plan_value}"
