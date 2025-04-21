from django.db import models

from apps.base.models import AbstractBaseModel


class ReportItem(AbstractBaseModel):
    report = models.ForeignKey(
        "reports.Report",
        on_delete=models.PROTECT,
        related_name="items"
    )
    statement_column = models.ForeignKey(
        "reports.StatementColumn",
        on_delete=models.PROTECT
    )
    value = models.PositiveIntegerField(default=0)