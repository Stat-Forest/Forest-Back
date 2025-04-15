from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from apps.base.models import AbstractBaseModel
from django.core.exceptions import ValidationError

from apps.utils.services import RegionChoices


class Organization(AbstractBaseModel):

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    region = models.CharField(max_length=10, choices=RegionChoices.choices)

    class Meta:
        verbose_name = _('organization')
        verbose_name_plural = _('organizations')

    def __str__(self):
        return self.name

    def clean(self):
        if not self.slug:
            self.slug = slugify(self.name)
        if Organization.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            raise ValidationError({'name': _('An organization with this name already exists.')})
