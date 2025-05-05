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
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_("Column Title")
    )
    plane = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Plane"),
    )
    is_only_plane = models.BooleanField(
        default=False,
        verbose_name=_("Is only-plane"),
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
