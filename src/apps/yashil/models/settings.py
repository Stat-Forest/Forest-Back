"""Versiyali modul qoidalari (TZ §24.1): har o'zgarish yangi versiya, `effective_from` dan kuchga kiradi."""
from django.conf import settings
from django.db import models

from apps.base.models import AbstractBaseModel


class YashilSetting(AbstractBaseModel):
    key = models.CharField(max_length=60, db_index=True, verbose_name="Kalit")
    value = models.JSONField(verbose_name="Qiymat")
    effective_from = models.DateField(verbose_name="Kuchga kirish sanasi")
    version = models.PositiveIntegerField(verbose_name="Versiya")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    note = models.CharField(max_length=500, blank=True, verbose_name="Asos / izoh")

    class Meta:
        verbose_name = "Modul qoidasi"
        verbose_name_plural = "Modul qoidalari (versiyali)"
        ordering = ["key", "-version"]
        constraints = [models.UniqueConstraint(fields=["key", "version"], name="yashil_setting_key_version_uniq")]

    def __str__(self):
        return f"{self.key} v{self.version} = {self.value} ({self.effective_from})"
