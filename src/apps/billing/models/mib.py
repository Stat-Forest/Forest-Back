"""
MIB Push Service (pushservice.egov.uz) ga yuborilgan shartnoma ma'lumotlari log'i
(billing-urmon.uz dagi `MibPushServiceLog` porti).
"""
import uuid

from django.db import models

from apps.base.models import AbstractBaseModel

from .contract import Contract


class MibPushLog(AbstractBaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        SENT = "sent", "Yuborildi"
        FAILED = "failed", "Xatolik"
        EXPIRED = "expired", "Muddati o'tdi"

    contract = models.ForeignKey(
        Contract, on_delete=models.SET_NULL, null=True, blank=True, related_name="mib_push_logs", verbose_name="Shartnoma",
    )
    contract_number = models.CharField(max_length=200, blank=True, default="", verbose_name="Shartnoma raqami")
    correlation_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name="Correlation ID")
    payload = models.JSONField(verbose_name="Yuborilgan ma'lumot")
    payload_hash = models.CharField(max_length=64, db_index=True, verbose_name="Ma'lumot hash'i")
    destination_subscribers = models.JSONField(default=list, blank=True, verbose_name="Qabul qiluvchilar")
    dtl = models.DateField(verbose_name="Push Service'da saqlanish muddati")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True, verbose_name="Holati")
    attempts = models.PositiveSmallIntegerField(default=0, verbose_name="Urinishlar")
    http_status = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="HTTP status")
    response = models.JSONField(null=True, blank=True, verbose_name="Javob")
    error = models.TextField(blank=True, default="", verbose_name="Xatolik")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Yuborilgan vaqt")

    class Meta:
        verbose_name = "MIB push log"
        verbose_name_plural = "MIB push loglari"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["contract", "status"])]

    def __str__(self) -> str:
        return f"{self.contract_number or self.contract_id} — {self.status}"
