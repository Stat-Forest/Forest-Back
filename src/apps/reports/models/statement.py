from django.db import models
from django.core.validators import FileExtensionValidator

from apps.utils.services import PeriodChoices
from apps.base.models import AbstractBaseModel


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
    icon = models.FileField(
        upload_to='statements/icons/%Y/%m/%d/',
        validators=[FileExtensionValidator(['svg'])],
        blank=True,
        null=True,
    )

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new and hasattr(self, "name_uz") and self.name_uz:
            if not hasattr(self, "name_ru") or not self.name_ru:
                self.name_ru = self.name_uz
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
