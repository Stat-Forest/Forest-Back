"""Yashil modellari uchun umumiy asos: saqlashdan oldin to'liq validatsiya, amal davri."""
from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.base.models import AbstractBaseModel


class ValidatedModel(AbstractBaseModel):
    """Har `save()` oldidan `full_clean()` — ma'lumotnoma yaxlitligi import va admin'da bir xil."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class PeriodMixin(models.Model):
    """`valid_from` .. `valid_to` (None = ochiq) amal davri."""

    valid_from = models.DateField(default=date.today, verbose_name="Amal qilish boshlanishi")
    valid_to = models.DateField(null=True, blank=True, verbose_name="Amal qilish tugashi")

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if self.valid_to and self.valid_from and self.valid_to < self.valid_from:
            raise ValidationError({"valid_to": "Tugash sanasi boshlanish sanasidan oldin bo'lishi mumkin emas."})

    def is_current(self, on: date | None = None) -> bool:
        on = on or date.today()
        if self.valid_from and on < self.valid_from:
            return False
        return self.valid_to is None or on <= self.valid_to


def period_overlap_q(valid_from, valid_to) -> Q:
    """Berilgan davr bilan kesishadigan yozuvlar sharti."""
    q = Q(valid_to__isnull=True) | Q(valid_to__gte=valid_from)
    if valid_to is not None:
        q &= Q(valid_from__lte=valid_to)
    return q


def ensure_single_active(instance, *, field: str, label: str) -> None:
    """Bir obyektga (masalan mahallaga) bir vaqtda bitta faol yozuv bo'lsin."""
    model = type(instance)
    qs = model.objects.filter(**{field: getattr(instance, field)}).filter(
        period_overlap_q(instance.valid_from, instance.valid_to)
    )
    if instance.pk:
        qs = qs.exclude(pk=instance.pk)
    if qs.exists():
        raise ValidationError({"valid_from": f"{label} uchun bu davrda boshqa faol yozuv bor."})
