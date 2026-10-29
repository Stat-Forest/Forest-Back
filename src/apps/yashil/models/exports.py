"""Hisobot eksport vazifalari (TZ §14.2: katta eksport fonda tayyorlanadi, tayyor bo'lganda xabar)."""
from django.conf import settings
from django.db import models

from apps.base.models import AbstractBaseModel
from apps.yashil.models.membership import YashilMembership


def export_upload_to(instance, filename):
    return f"documents/yashil/exports/{instance.created_at:%Y/%m}/{instance.id}.{instance.format}"


class ExportJob(AbstractBaseModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Navbatda"
        RUNNING = "running", "Tayyorlanmoqda"
        DONE = "done", "Tayyor"
        FAILED = "failed", "Xato"
        EXPIRED = "expired", "Muddati o'tgan (fayl o'chirilgan)"

    class Kind(models.TextChoices):
        REGISTRY = "registry", "Buyurtmalar reestri"
        ACTS = "acts", "Dalolatnomalar reestri"

    class Format(models.TextChoices):
        XLSX = "xlsx", "XLSX"
        CSV = "csv", "CSV"
        PDF = "pdf", "PDF"

    ACTIVE_STATUSES = (Status.QUEUED, Status.RUNNING)

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="yashil_exports")
    membership = models.ForeignKey(YashilMembership, on_delete=models.SET_NULL, null=True, blank=True, related_name="exports",
                                   help_text="Kabinet (ko'lam); modul admini uchun bo'sh")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    format = models.CharField(max_length=5, choices=Format.choices)
    filters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED, db_index=True)
    row_count = models.PositiveIntegerField(default=0)
    file = models.FileField(upload_to=export_upload_to, null=True, blank=True)
    error = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Eksport vazifasi"
        verbose_name_plural = "Eksport vazifalari"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} · {self.format} · {self.status}"
