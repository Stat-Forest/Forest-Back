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
        null=True,
        blank=True
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_("Column Title")
    )
    ordering = models.FloatField(
        default=0,
        verbose_name=_("Ordering"),
        validators=[MinValueValidator(0.0)]
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _("Statement Column")
        verbose_name_plural = _("Statement Columns")
        ordering = ["ordering"]
        unique_together = ("statement", "title")

[
  {
    "id": 1,
    "statement": 1,
    "title": "1 - chorak",
    "ordering": 1,
    "children": [
      {
        "id": 2,
        "statement": 1,
        "title": "Yanvar",
        "ordering": 1,
        "children": [
          {
            "id": 3,
            "statement": 1,
            "title": "Reja",
            "ordering": 1,
            "children": []
          },
          ...
        ]
      },
      ...
    ]
  }
]