"""
Bekor qilish (TZ §9.3; javob Е4) va tungi solishtirish yozuvlari (TZ §22.3).

Qabuldan keyin bekor qilish uch tomonlama: so'rov (mahalla yoki yetkazib beruvchi) →
ikkinchi tomon kelishuvi → uyushma tasdig'i. Tasdiqda faqat yetkazilmagan va qabul
qilinmagan qismga ajratish tiklanadi; imzolangan hujjatlar o'zgarmaydi, elektron
bekor qilish hujjati (`Document.kind = cancellation`) yaratiladi.
"""
from django.db import models

from apps.base.models import AbstractBaseModel
from apps.yashil.models.membership import YashilMembership
from apps.yashil.models.orders import Order


class CancelRequest(AbstractBaseModel):
    class Status(models.TextChoices):
        REQUESTED = "requested", "So'ralgan"
        AGREED = "agreed", "Ikkinchi tomon kelishgan"
        APPROVED = "approved", "Uyushma tasdiqlagan"
        REJECTED = "rejected", "Rad etilgan"

    class Party(models.TextChoices):
        MAHALLA = "mahalla", "Mahalla"
        SUPPLIER = "supplier", "Yetkazib beruvchi"

    OPEN_STATUSES = (Status.REQUESTED, Status.AGREED)

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="cancel_requests")
    requested_by_party = models.CharField(max_length=10, choices=Party.choices)
    requested_by_membership = models.ForeignKey(YashilMembership, on_delete=models.PROTECT, related_name="+")
    is_full = models.BooleanField(default=True)
    lines = models.JSONField(default=list, blank=True, help_text="[{order_line_id, code, name_cyr, unit, qty}] — bo'sh = butun qoldiq")
    reason = models.TextField(max_length=4000)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.REQUESTED, db_index=True)
    agreed_by = models.ForeignKey(YashilMembership, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    agreed_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(YashilMembership, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(max_length=4000, blank=True)
    document = models.ForeignKey("yashil.Document", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    result = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Bekor qilish so'rovi"
        verbose_name_plural = "Bekor qilish so'rovlari"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["order", "status"])]

    def __str__(self):
        return f"{self.order.display_number} — {self.get_status_display()}"


class ReconcileIssue(models.Model):
    """Tungi solishtirishda topilgan nomuvofiqlik; yo'qolganda `resolved_at` to'ldiriladi."""

    kind = models.CharField(max_length=40, db_index=True)
    key = models.CharField(max_length=120, help_text="Takror yozmaslik uchun kalit (qator/ombor+pozitsiya/buyurtma)")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True, related_name="reconcile_issues")
    warehouse = models.ForeignKey("yashil.Warehouse", on_delete=models.CASCADE, null=True, blank=True, related_name="reconcile_issues")
    details = models.JSONField(default=dict, blank=True)
    found_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Solishtirish nomuvofiqligi"
        verbose_name_plural = "Solishtirish nomuvofiqliklari"
        ordering = ["-found_at"]
        indexes = [models.Index(fields=["kind", "key", "resolved_at"])]

    def __str__(self):
        return f"{self.kind} {self.key}"
