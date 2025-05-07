from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models import AbstractBaseModel


class StatementColumn(AbstractBaseModel):
    statement = models.ForeignKey(
        'reports.Statement',
        on_delete=models.CASCADE,
        related_name='columns',
        limit_choices_to={'parent__isnull': False},
        blank=True,
        null=True,
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_query_name="statement_columns",
        null=True,
        blank=True
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_("Column Title")
    )
    ordering = models.CharField(
        default=0,
        verbose_name=_("Ordering")
    )
    is_plane = models.BooleanField(default=False)

    def return_parent(self):
        if self.parent is None:
            return self.title
        return f"{self.parent.return_parent()} - {self.title}"
    def __str__(self):

        return self.return_parent()

    class Meta:
        verbose_name = _("Statement Column")
        verbose_name_plural = _("Statement Columns")
        ordering = ["ordering"]
        unique_together = ("statement", "title")

