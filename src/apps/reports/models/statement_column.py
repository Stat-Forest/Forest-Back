# apps/reports/models/statement_column.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.base.models import AbstractBaseModel


class StatementColumn(AbstractBaseModel):
    class PlanStatus(models.TextChoices):
        YANVAR = 'yanvar', 'Yanvar'
        FEVRAL = 'fevral', 'Fevral'
        MART = 'mart', 'Mart'
        APREL = 'aprel', 'Aprel'
        MAY = 'may', 'May'
        IYUN = 'iyun', 'Iyun'
        IYUL = 'iyul', 'Iyul'
        AVGUST = 'avgust', 'Avgust'
        SENTABR = 'sentabr', 'Sentabr'
        OKTABR = 'oktabr', 'Oktabr'
        NOYABR = 'noyabr', 'Noyabr'
        DEKABR = 'dekabr', 'Dekabr'

        CHORAK_1 = 'chorak_1', '1-chorak'
        CHORAK_2 = 'chorak_2', '2-chorak'
        CHORAK_3 = 'chorak_3', '3-chorak'
        CHORAK_4 = 'chorak_4', '4-chorak'

        YILLIK = 'yillik', 'Yillik'

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
    is_organization = models.BooleanField(
        default=False
    )

    status_plan = models.CharField(
        max_length=20,
        choices=PlanStatus.choices,
        blank=True,
        null=True,
        verbose_name=_("Plan holati (oy, chorak, yil)")
    )

    def clean(self):
        super().clean()
        if self.status_plan and self.is_organization:
            raise ValidationError("An instance cannot be both a plan and an organization at the same time.")

    # def return_parent(self):
    #     if self.parent is None:
    #         return self.title
    #     return f"{self.parent.return_parent()} - {self.title}"

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _("Statement Column")
        verbose_name_plural = _("Statement Columns")
        unique_together = ("statement", "title",'parent','ordering')
        ordering = ["ordering"]
