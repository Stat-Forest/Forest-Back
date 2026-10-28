"""
Hujjat, o'zgarmas versiya va imzo (TZ §11–§13, §20).

`DocumentVersion.content` — blanka maydonlari (JSON), `html` — bosma ko'rinish,
`content_hash` — kanonik JSON sha256, `qr_token` — ochiq tekshirish sahifasi
identifikatori (taxmin qilib bo'lmaydi, shaxsiy ma'lumot yo'q).
"""
import hashlib
import json
import secrets

from django.conf import settings
from django.db import models

from apps.base.models import AbstractBaseModel
from apps.yashil.models.membership import YashilMembership


def canonical_hash(content: dict) -> str:
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


class Document(AbstractBaseModel):
    class Kind(models.TextChoices):
        ORDER_FORM = "order_form", "Buyurtmanoma"
        ACT = "act", "Topshirish-qabul qilish dalolatnomasi"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    order = models.ForeignKey("yashil.Order", on_delete=models.CASCADE, related_name="documents")
    number = models.CharField(max_length=40, blank=True)
    current_version = models.ForeignKey("yashil.DocumentVersion", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        verbose_name = "Hujjat"
        verbose_name_plural = "Hujjatlar"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} {self.number}"


class DocumentVersion(AbstractBaseModel):
    class Status(models.TextChoices):
        UNSIGNED = "unsigned", "Imzolanmagan"
        SIGNED = "signed", "Imzolangan"
        SUPERSEDED = "superseded", "Almashtirilgan"
        CANCELLED = "cancelled", "Bekor qilingan"

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version_no = models.PositiveIntegerField()
    template_version = models.PositiveSmallIntegerField(default=1)
    content = models.JSONField()
    html = models.TextField(blank=True)
    content_hash = models.CharField(max_length=64, db_index=True, editable=False)
    qr_token = models.CharField(max_length=32, unique=True, editable=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.UNSIGNED)
    pdf_file = models.FileField(upload_to="documents/yashil/pdf/", null=True, blank=True)

    class Meta:
        ordering = ["-version_no"]
        constraints = [models.UniqueConstraint(fields=["document", "version_no"], name="yashil_docversion_uniq")]

    def save(self, *args, **kwargs):
        if not self.content_hash:
            self.content_hash = canonical_hash(self.content or {})
        if not self.qr_token:
            self.qr_token = secrets.token_urlsafe(16)[:22]
        super().save(*args, **kwargs)

    @property
    def signatures_by_role(self) -> dict:
        return {s.role: s for s in self.signatures.all()}


class Signature(AbstractBaseModel):
    """Bir hujjat versiyasiga bir tomondan bitta imzo (TZ §20 cheklovi)."""

    class Role(models.TextChoices):
        MAHALLA = "mahalla", "Mahalla"
        SUPPLIER = "supplier", "Yetkazib beruvchi"

    document_version = models.ForeignKey(DocumentVersion, on_delete=models.CASCADE, related_name="signatures")
    signer_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="yashil_signatures")
    signer_membership = models.ForeignKey(YashilMembership, on_delete=models.PROTECT, null=True, blank=True, related_name="signatures")
    role = models.CharField(max_length=10, choices=Role.choices)
    signer_cn = models.CharField(max_length=255, blank=True)
    signer_tin = models.CharField(max_length=20, blank=True)
    signer_pinfl = models.CharField(max_length=20, blank=True)
    cert_serial = models.CharField(max_length=64, blank=True)
    cert_valid_from = models.CharField(max_length=32, blank=True)
    cert_valid_to = models.CharField(max_length=32, blank=True)
    signed_at = models.DateTimeField(auto_now_add=True)
    mode = models.CharField(max_length=10)
    pkcs7 = models.TextField()
    verify_result = models.JSONField(default=dict, blank=True)
    is_valid = models.BooleanField(default=False)

    class Meta:
        ordering = ["signed_at"]
        constraints = [models.UniqueConstraint(fields=["document_version", "role"], name="yashil_signature_role_uniq")]
