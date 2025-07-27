from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.utils.services import RegionChoices
from apps.base.models import AbstractBaseModel


class Republic(AbstractBaseModel):
    name = models.CharField(max_length=255)
    # slug = models.SlugField(max_length=255, unique=True)
    
    # def save(self, *args, **kwargs):
    #     if not self.slug:
    #         self.slug = slugify(self.name)
    #     return super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Republic")
        verbose_name_plural = _("Republics")
        ordering = ["name"]


class Organization(AbstractBaseModel):
    name = models.CharField(
        max_length=255,
        verbose_name=_("Name")
    )
    republic = models.ForeignKey(
        Republic,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="organizations"
    )
    region = models.CharField(
        max_length=50,
        choices=RegionChoices.choices,
        verbose_name=_("Region")
    )

    stir = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"
