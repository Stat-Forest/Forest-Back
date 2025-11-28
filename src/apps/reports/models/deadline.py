from django.db import models
from django.db.models import Q, UniqueConstraint
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

    deadline_at = models.DateField(
        verbose_name=_("Deadline date"),
        help_text=_("Final deadline day (format: DD/MM/YYYY)"),
        blank=True,
        null=True,
    )

    def __str__(self):
        return f'{self.statement.name} : {self.submit_at}'

    class Meta:
        verbose_name = "Muddat"
        verbose_name_plural = "Muddatlar"

        constraints = [
            # Daily
            UniqueConstraint(
                fields=['statement', 'submit_at'],
                condition=Q(statement__period='daily'),
                name='unique_statement_submit_at_daily'
            ),
            # Weekly
            UniqueConstraint(
                fields=['statement', 'submit_at'],
                condition=Q(statement__period='weekly'),
                name='unique_statement_submit_at_weekly'
            ),
            # Monthly
            UniqueConstraint(
                fields=['statement', 'submit_at'],
                condition=Q(statement__period='monthly'),
                name='unique_statement_submit_at_monthly'
            ),
            # Quarterly
            UniqueConstraint(
                fields=['statement', 'submit_at'],
                condition=Q(statement__period='quarterly'),
                name='unique_statement_submit_at_quarterly'
            ),
            # Yearly
            UniqueConstraint(
                fields=['statement', 'submit_at'],
                condition=Q(statement__period='yearly'),
                name='unique_statement_submit_at_yearly'
            ),
        ]
