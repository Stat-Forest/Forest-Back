from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.base.models import AbstractBaseModel



class ReportItem(AbstractBaseModel):
    report = models.ForeignKey(
        "reports.Report",
        on_delete=models.CASCADE,
        related_name="report_items",
        verbose_name=_("Report")
    )
    plant = models.ForeignKey(
        "reports.Plant",
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    statement_column = models.ForeignKey(
        "reports.StatementColumn",
        on_delete=models.PROTECT,
        related_name="items",
        verbose_name=_("Statement Column")
    )
    value = models.TextField(blank=True, null=True)

    def __str__(self):
        plant_name = self.plant.name if self.plant else _("No Plant")
        return f"Report {self.report.id} | Column: {self.statement_column.title_uz}  Value: {self.value}"

    class Meta:
        verbose_name = _("Report Item")
        verbose_name_plural = _("Report Items")
        # unique_together = ("report", "statement_column", "plant")


class ReportItemInner(AbstractBaseModel):
    report_item = models.ForeignKey(
        "reports.ReportItem",
        on_delete=models.CASCADE,
        related_name="inners"
    )
    value = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Value"),
    )

    def __str__(self):
        return f"Inner of ReportItem {self.report_item.id} | Value: {self.value}"
