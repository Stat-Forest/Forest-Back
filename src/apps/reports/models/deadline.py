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
        max_length=20,
        help_text=_(
           f'Kunlik-YYYY-MM-DD , '
           f'Haftalik -YYYY-MM-W(1,2,3,4), '
           f'Oylik -YYYY-MM, '
           f'Choraklik-YYYY-Qx(Q1,Q2,Q3,Q4)'
           f'Yillik-YYYY'
        )

    )

    def __str__(self):
        return f'{self.statement.name} : {self.submit_at}'

    class Meta:
        verbose_name = _("Deadline")
        verbose_name_plural = _("Deadlines")


