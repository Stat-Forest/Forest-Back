from django.db import models
from apps.base.models import AbstractBaseModel
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.utils.services import RegionChoices


class Organization(AbstractBaseModel):

    name = models.CharField(max_length=255)
    region = models.CharField(max_length=10, choices=RegionChoices.choices)

    class Meta:
        verbose_name = _('organization')
        verbose_name_plural = _('organizations')

    def clean(self):
        super().clean()
        if self.region not in RegionChoices.choices:
            raise ValidationError({
                'region': _('This field is not a valid choice.'),
            })
    def __str__(self):
        return self.name

