from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.utils.services import RegionChoices
from apps.base.models import AbstractBaseModel


class Organization(AbstractBaseModel):
    name = models.CharField(
        max_length=255,
        verbose_name=_("Name")
    )
    region = models.CharField(
        max_length=50,
        choices=RegionChoices.choices,
        verbose_name=_("Region")
    )

    stir = models.PositiveBigIntegerField()

    class Meta:
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"
