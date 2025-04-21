from django.db import models
from apps.base.models import AbstractBaseModel
from apps.utils.services import StatementChoices

class Report(AbstractBaseModel):
    class StatusChoices(models.TextChoices):
        NEW = 'new', 'New'
        SENT = 'sent', 'Sent'
        CANCELLED = 'cancelled', 'Cancelled'
        EXCEPTED = 'excepted', 'Excepted'

    organization = models.ForeignKey(
        "general.Organization",
        on_delete=models.PROTECT,
    )
    statement = models.CharField(
        max_length=255,
        choices=StatementChoices.choices
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices
    )

    def __str__(self):
        return f"{self.organization.title} - {self.statement} "



