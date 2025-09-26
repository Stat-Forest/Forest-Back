from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.base.models import AbstractBaseModel


class StatementColumnManager(models.Manager):
    def get_by_natural_key(self, statement_name, title, parent_key, ordering):
        parent = None
        if parent_key:
            parent = self.get_by_natural_key(*parent_key)
        return self.get(
            statement__name=statement_name,
            title=title,
            parent=parent,
            ordering=ordering,
        )


class StatementColumn(AbstractBaseModel):
    class PlanStatus(models.TextChoices):
        YANVAR = 'yanvar', _('Yanvar')
        FEVRAL = 'fevral', _('Fevral')
        MART = 'mart', _('Mart')
        APREL = 'aprel', _('Aprel')
        MAY = 'may', _('May')
        IYUN = 'iyun', _('Iyun')
        IYUL = 'iyul', _('IYul')
        AVGUST = 'avgust', _('Avgust')
        SENTABR = 'sentabr', _('Sentabr')
        OKTABR = 'oktabr', _('Oktabr')
        NOYABR = 'noyabr', _('Noyabr')
        DEKABR = 'dekabr', _('Dekabr')

        CHORAK_1 = 'chorak_1', _('1-chorak')
        CHORAK_2 = 'chorak_2', _('2-chorak')
        CHORAK_3 = 'chorak_3', _('3-chorak')
        CHORAK_4 = 'chorak_4', _('4-chorak')

        YILLIK = 'yillik', _('Yillik')
        YILLIK_TOTAL = 'yillik_total', _('Yillik Total')

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
        max_length=500,
        verbose_name=_("Column Title")
    )
    ordering = models.CharField(
        default="0",
        max_length=100,
        verbose_name=_("Ordering")
    )
    is_organization = models.BooleanField(default=False)

    status_plan = models.CharField(
        max_length=20,
        choices=PlanStatus.choices,
        blank=True,
        null=True,
        verbose_name=_("Plan holati (oy, chorak, yil)")
    )
    is_user_input = models.BooleanField(default=True)

    objects = StatementColumnManager()

    @property
    def return_parent(self):
        if self.parent is None:
            return self.title
        return f"{self.parent.return_parent} - {self.title}"

    def __str__(self):
        return self.return_parent

    @property
    def is_leaf(self):
        return not StatementColumn.objects.filter(parent=self).exists()

    def clean(self):
        super().clean()
        if self.status_plan and self.is_organization:
            raise ValidationError(_("An instance cannot be both a plan and an organization at the same time."))

    # ✅ Natural key
    def natural_key(self):
        return (
            self.statement.name if self.statement else None,
            self.title,
            self.parent.natural_key() if self.parent else None,
            self.ordering,
        )
    natural_key.dependencies = ["reports.statement"]

    class Meta:
        verbose_name = _("Statement Column")
        verbose_name_plural = _("Statement Columns")
        unique_together = ("statement", "title", "parent", "ordering")
        ordering = ["ordering"]
