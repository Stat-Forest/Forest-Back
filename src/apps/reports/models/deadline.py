from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models import AbstractBaseModel


class Deadline(AbstractBaseModel):
    organizations = models.ManyToManyField(
        "general.Organization",
        verbose_name=_("Organizations"),
        related_name="deadlines"
    )
    statement = models.ForeignKey(
        "reports.Statement",
        on_delete=models.CASCADE,
        limit_choices_to={
            'parent__isnull': False,
        }

    )
    submit_at = models.CharField(
        max_length=100,
        help_text=_(
            'Kunlik - YYYY-MM-DD, '
            'Haftalik - YYYY-MM-HAFTALIK_1 / HAFTALIK_2 / HAFTALIK_3 / HAFTALIK_4, '
            'Oylik - YYYY-MM, '
            'Choraklik - YYYY-CHORAK_1 / CHORAK_2 / CHORAK_3 / CHORAK_4, '
            'Yillik - YYYY'
        )
    )

    def __str__(self):
        return f'{self.statement.name} : {self.submit_at}'

    class Meta:
        verbose_name = "Muddat"
        verbose_name_plural = "Muddatlar"


