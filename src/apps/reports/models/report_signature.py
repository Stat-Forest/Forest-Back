from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models import AbstractBaseModel


class ReportSignature(AbstractBaseModel):
    """
    Hisobot yuborilganda tashkilot rahbari qo'ygan E-imzo (PKCS#7) imzosi.

    `document` — imzolangan matn (hisobot ma'lumotlari hash'i bilan),
    `pkcs7` — vaqt tamg'asi qo'shilgan PKCS#7, `verify_result` — e-imzo-server
    tekshiruvining qisqartirilgan javobi. Yozuv o'zgartirilmaydi: hisobot
    qaytarilib qayta yuborilsa yangi imzo yaratiladi.
    """

    report = models.ForeignKey(
        "reports.Report",
        on_delete=models.CASCADE,
        related_name="signatures",
    )
    quarter = models.CharField(
        max_length=2, null=True, blank=True,
        help_text=_("Daromad hisobotida imzolangan chorak (q1..q4)"),
    )
    signer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="report_signatures",
    )
    signer_cn = models.CharField(max_length=255, blank=True)
    signer_tin = models.CharField(max_length=20, blank=True)
    signer_pinfl = models.CharField(max_length=20, blank=True)
    cert_serial = models.CharField(max_length=64, blank=True)
    cert_valid_from = models.CharField(max_length=32, blank=True)
    cert_valid_to = models.CharField(max_length=32, blank=True)

    signed_at = models.DateTimeField()
    document = models.TextField()
    document_hash = models.CharField(max_length=64, db_index=True)
    items_hash = models.CharField(max_length=64)
    pkcs7 = models.TextField()
    verify_status = models.IntegerField(default=0)
    verify_result = models.JSONField(default=dict, blank=True)
    is_valid = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Hisobot imzosi")
        verbose_name_plural = _("Hisobot imzolari")

    def __str__(self):
        return f"{self.signer_cn} — {self.report_id} ({self.signed_at:%Y-%m-%d %H:%M})"
