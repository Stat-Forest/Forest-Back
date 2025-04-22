from django.db import models
from apps.base.models import AbstractBaseModel
from apps.utils.services import StatementChoices


class StatementColumn(AbstractBaseModel):
    statement = models.CharField(max_length=255, choices=StatementChoices.choices)
    title = models.CharField(max_length=255)
    ordering = models.PositiveIntegerField()

    def __str__(self):
        return self.title