from django.db import models

from apps.base.models import AbstractBaseModel


class Organization(AbstractBaseModel):
    name = models.CharField(max_length=350)
    slug = models.SlugField(max_length=350, unique=True)

    def __str__(self):
        return self.name


class Position(AbstractBaseModel):
    name = models.CharField(max_length=350)
    slug = models.SlugField(max_length=350, unique=True)