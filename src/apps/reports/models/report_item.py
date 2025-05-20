from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.base.models import AbstractBaseModel



class ReportItem(AbstractBaseModel):
    report = models.ForeignKey(
        "reports.Report",
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Report")
    )
    statement_column = models.ForeignKey(
        "reports.StatementColumn",
        on_delete=models.PROTECT,
        related_name="report_items",
        verbose_name=_("Statement Column")
    )
    value = models.CharField(
        max_length=100,
        verbose_name=_("Value"),
    )

    def __str__(self):
        return f"{self.report.id} - {self.value}"

    class Meta:
        verbose_name = _("Report Item")
        verbose_name_plural = _("Report Items")
        unique_together = ("report", "statement_column")
