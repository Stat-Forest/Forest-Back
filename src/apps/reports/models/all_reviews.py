from django.core.validators import MinValueValidator
from django.db import models

from apps.base.models import AbstractBaseModel
from apps.utils.services import AllReviews


class AllReview(AbstractBaseModel):
    title = models.CharField(
        max_length=120,
        choices=AllReviews
    )
    count = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name_plural = 'all reports'
        ordering = ['-count']

    def __str__(self):
        return self.title