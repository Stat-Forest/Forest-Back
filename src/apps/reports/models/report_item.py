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
    statement_column = models.ForeignKey(
        "reports.StatementColumn",
        on_delete=models.PROTECT,
        related_name="items",
        verbose_name=_("Statement Column")
    )
    value = models.TextField(blank=True, null=True)

    def __str__(self):
        # Avoid dereferencing FK to StatementColumn to prevent extra queries in admin/logs
        return f"Report {getattr(self, 'report_id', None)} | ColumnID: {getattr(self, 'statement_column_id', None)}  Value: {self.value}"

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
    plant = models.ForeignKey(
        "reports.Plant",
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    value = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Value"),
    )

    def __str__(self):
        # Avoid dereferencing FK to ReportItem to prevent extra queries in admin/logs
        return f"Inner of ReportItemID {getattr(self, 'report_item_id', None)} | Value: {self.value}"
