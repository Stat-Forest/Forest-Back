"""Ishlab chiqarish kalendari: bayramlar va ko'chirilgan ish kunlari (TZ §8.1; javob Д1)."""
from django.conf import settings
from django.db import models

from apps.base.models import AbstractBaseModel


class CalendarDay(AbstractBaseModel):
    class Kind(models.TextChoices):
        HOLIDAY = "holiday", "Dam olish / bayram"
        WORKDAY = "workday", "Ko'chirilgan ish kuni"

    date = models.DateField(unique=True, verbose_name="Sana")
    kind = models.CharField(max_length=10, choices=Kind.choices, verbose_name="Turi")
    note = models.CharField(max_length=200, blank=True, verbose_name="Izoh")
    source_ref = models.CharField(max_length=300, blank=True, verbose_name="Manba hujjat rekviziti")
    source_file = models.FileField(upload_to="documents/yashil/calendar/", null=True, blank=True)
    version = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = "Kalendar kuni"
        verbose_name_plural = "Ishlab chiqarish kalendari"
        ordering = ["date"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        _invalidate()

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        _invalidate()
        return result

    def __str__(self):
        return f"{self.date} — {self.get_kind_display()}"


def _invalidate():
    from apps.yashil.services.workdays import invalidate_calendar_cache

    invalidate_calendar_cache()
