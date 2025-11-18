from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.base.models import AbstractBaseModel



class Plant(AbstractBaseModel):
    name = models.CharField(max_length=255)

    statement = models.ForeignKey(
        "reports.Statement",
        on_delete=models.CASCADE,
        related_name="plants",
        blank=True,
        null=True
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='children'
    )

    def clean(self):
        if self.parent and self.parent_id == self.id:
            raise ValidationError(_("Plant cannot be parent of itself."))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "O'simlik turi va nomi"
        verbose_name_plural = "O'simlik turi va nomlari"


class ColumnPlant(AbstractBaseModel):
    column = models.ForeignKey("reports.StatementColumn",
                               on_delete=models.PROTECT,
                               related_name='column_plants'
                               )
    plant = models.ForeignKey(Plant,
                              on_delete=models.PROTECT,
                              related_name='plant_columns'
                              )
    ordering = models.PositiveIntegerField(default=0)


    def clean(self):
        if self.plant.children.exists():
            raise ValidationError(_("Only leaf-level plants can be assigned to a column."))


    def __str__(self):
        return f"{self.ordering}"

    class Meta:
        verbose_name = "ColumnPlant of Plant"
        verbose_name_plural = "ColumnPlants of Plants"
        unique_together = ("column", "plant")
        ordering = ["ordering"]
