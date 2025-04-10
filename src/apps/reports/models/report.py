from src.apps.base.models import AbstractBaseModel
from django.db import models


class Report(AbstractBaseModel):
    class ReportType(models.TextChoices):
        Sent = 'sent', 'Sent'
        Returned = 'returned', 'Returned'
        Accepted = 'accepted', 'Accepted'

    title = models.CharField(
        max_length=255
    )
    name = models.CharField(
        max_length=255
    )
    period = models.CharField(
        max_length=50
    )
    type = models.CharField(
        max_length=255,
        default=ReportType.Sent
    )

    def __str__(self):
        return self.title
