"""Kabinet xabarnomalari (TZ §22.4) va takror so'rovdan himoya (TZ §16.2, §21)."""
from django.conf import settings
from django.db import models

from apps.yashil.models.membership import YashilMembership


class YashilNotification(models.Model):
    class Kind(models.TextChoices):
        ORDER_NEW_UNION = "order_new_union", "Uyushmaga yangi buyurtma"
        ORDER_FORWARDED = "order_forwarded", "Yetkazib beruvchiga yo'llandi"
        ORDER_RETURNED = "order_returned", "Buyurtma qaytarildi"
        ORDER_ACCEPTED = "order_accepted", "Ijroga qabul qilindi"
        ACT_SENT = "act_sent", "Akt mahallaga yuborildi"
        ACT_RETURNED = "act_returned", "Akt qaytarildi"
        ACT_APPROVED = "act_approved", "Akt qabul qilindi"
        DEADLINE_REMINDER = "deadline_reminder", "Muddat eslatmasi"
        OVERDUE = "overdue", "Muddat buzildi"
        STOCK_NEGATIVE = "stock_negative", "Manfiy qoldiq"
        CANCEL_REQUESTED = "cancel_requested", "Bekor qilish so'rovi"
        CANCEL_AGREED = "cancel_agreed", "Bekor qilishga kelishildi"
        CANCEL_APPROVED = "cancel_approved", "Bekor qilish tasdiqlandi"
        CANCEL_REJECTED = "cancel_rejected", "Bekor qilish rad etildi"
        RECONCILE_ISSUE = "reconcile_issue", "Solishtirish nomuvofiqligi"

    recipient_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="yashil_notifications")
    membership = models.ForeignKey(YashilMembership, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    kind = models.CharField(max_length=30, choices=Kind.choices)
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=1000, blank=True)
    order = models.ForeignKey("yashil.Order", on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient_user", "read_at"])]


class IdempotencyRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    key = models.CharField(max_length=128)
    path = models.CharField(max_length=300)
    request_hash = models.CharField(max_length=64)
    status_code = models.PositiveSmallIntegerField()
    response = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "key", "path"], name="yashil_idempotency_uniq")]
        indexes = [models.Index(fields=["created_at"])]
