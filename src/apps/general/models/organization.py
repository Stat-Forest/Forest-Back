from django.db import models
from apps.base.models import AbstractBaseModel
from django.utils.translation import gettext_lazy as _

from apps.utils.services import RegionChoices


class Organization(AbstractBaseModel):

    name = models.CharField(max_length=255)
    region = models.CharField(max_length=50, choices=RegionChoices.choices)

    class Meta:
        verbose_name = _('organization')
        verbose_name_plural = _('organizations')

    def __str__(self):
        return self.name

