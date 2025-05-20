# apps/reports/models/statement_column.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.base.models import AbstractBaseModel


class StatementColumn(AbstractBaseModel):
    statement = models.ForeignKey(
        'reports.Statement',
        on_delete=models.CASCADE,
        related_name='columns',
        blank=True,
        null=True,
        limit_choices_to={'parent__isnull': False},
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_("Column Title")
    )
    ordering = models.CharField(
        default="0",
        max_length=100,
        verbose_name=_("Ordering")
    )
    is_plan = models.BooleanField(
        default=False
    )
    is_organization = models.BooleanField(
        default=False
    )
    def clean(self):
        super().clean()
        if self.is_plan and self.is_organization:
            raise ValidationError("An instance cannot be both a plan and an organization at the same time.")

    def return_parent(self):
        if self.parent is None:
            return self.title
        return f"{self.parent.return_parent()} - {self.title}"

    def __str__(self):
        return self.return_parent()

    class Meta:
        verbose_name = _("Statement Column")
        verbose_name_plural = _("Statement Columns")
        unique_together = ("statement", "title",'parent','ordering')
        ordering = ["ordering"]
