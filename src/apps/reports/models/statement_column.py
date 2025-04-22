from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models import AbstractBaseModel
from apps.utils.services import StatementChoices


class StatementColumn(AbstractBaseModel):
    statement = models.CharField(
        max_length=255,
        choices=StatementChoices.choices,
        verbose_name=_("Statement")
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_("Column Title")
    )
    ordering = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Ordering")
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _("Statement Column")
        verbose_name_plural = _("Statement Columns")
        ordering = ["ordering"]
        unique_together = ("statement", "title")
