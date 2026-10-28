"""
Topshirish-qabul qilish dalolatnomasi (TZ §10, §12, §22.2).

`Act` — buyurtma bo'yicha partiya akti (`<buyurtma>/A<n>`); qaytarilgan akt
tuzatilsa o'sha aktning yangi `ActVersion`i (raqam o'zgarmaydi), yangi partiya —
yangi akt. Qabul miqdori faqat ikki tomon imzolagan (approved) aktlardan hisoblanadi;
akt tasdig'i omborni o'zgartirmaydi.
"""
from django.conf import settings
from django.db import models

from apps.base.models import AbstractBaseModel
from apps.yashil.models.membership import YashilMembership
from apps.yashil.models.orders import Order, OrderLine, validate_attachment


class ActReturnReason(models.TextChoices):
    DOCUMENT = "document", "Hujjat xatosi"
    QUANTITY = "quantity", "Miqdor farqi"
    QUALITY = "quality", "Sifat"
    NOT_DELIVERED = "not_delivered", "Amalda yetkazilmagan"
    OTHER = "other", "Boshqa"


ACT_RETURN_REASON_CYR = {
    ActReturnReason.DOCUMENT: "Ҳужжат хатоси",
    ActReturnReason.QUANTITY: "Миқдор фарқи",
    ActReturnReason.QUALITY: "Сифат",
    ActReturnReason.NOT_DELIVERED: "Амалда етказилмаганлик",
    ActReturnReason.OTHER: "Бошқа",
}


class Act(AbstractBaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        REVIEW = "mahalla_review", "Mahalla tasdig'ida"
        APPROVED = "approved", "Qabul qilingan"
        RETURNED = "returned", "Tuzatish uchun qaytarilgan"
        CANCELLED = "cancelled", "Bekor qilingan"

    OPEN_STATUSES = (Status.DRAFT, Status.REVIEW, Status.RETURNED)

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="acts")
    index = models.PositiveSmallIntegerField()
    number = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True)
    version_no = models.PositiveIntegerField(default=1)
    current_version = models.ForeignKey("yashil.ActVersion", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    document = models.ForeignKey("yashil.Document", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    is_partial = models.BooleanField(default=False, help_text="Shu aktdan keyin ham qabul qilinmagan hajm qoladi")
    approved_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Dalolatnoma"
        verbose_name_plural = "Dalolatnomalar"
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["order", "index"], name="yashil_act_index_uniq")]
        indexes = [models.Index(fields=["order", "status"])]

    def __str__(self):
        return self.number


class ActVersion(AbstractBaseModel):
    act = models.ForeignKey(Act, on_delete=models.CASCADE, related_name="versions")
    version_no = models.PositiveIntegerField()
    snapshot = models.JSONField(default=dict)
    document_version = models.ForeignKey("yashil.DocumentVersion", on_delete=models.SET_NULL, null=True, blank=True, related_name="act_versions")
    delivery_date = models.DateField(verbose_name="Haqiqiy yetkazish sanasi")
    planned_date = models.DateField(null=True, blank=True)
    responsible = models.CharField(max_length=300, blank=True, verbose_name="Mas'ul shaxs")
    delivery_address = models.CharField(max_length=500, blank=True)
    note = models.TextField(max_length=4000, blank=True)
    created_by_membership = models.ForeignKey(YashilMembership, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    submitted_at = models.DateTimeField(null=True, blank=True, help_text="Yetkazib beruvchi imzolagan vaqt")
    superseded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-version_no"]
        constraints = [models.UniqueConstraint(fields=["act", "version_no"], name="yashil_actversion_uniq")]


class ActLine(AbstractBaseModel):
    act_version = models.ForeignKey(ActVersion, on_delete=models.CASCADE, related_name="lines")
    order_line = models.ForeignKey(OrderLine, on_delete=models.PROTECT, related_name="act_lines")
    qty = models.DecimalField(max_digits=18, decimal_places=4)

    class Meta:
        ordering = ["order_line__position", "created_at"]
        constraints = [models.UniqueConstraint(fields=["act_version", "order_line"], name="yashil_actline_uniq")]


def act_attachment_upload_to(instance, filename):
    return f"documents/yashil/acts/{instance.act_id}/{filename}"


class ActAttachment(AbstractBaseModel):
    class Kind(models.TextChoices):
        PHOTO = "photo", "Foto"
        PDF = "pdf", "PDF"
        OTHER = "other", "Boshqa"

    act = models.ForeignKey(Act, on_delete=models.CASCADE, related_name="attachments")
    version_no = models.PositiveIntegerField(default=1)
    file = models.FileField(upload_to=act_attachment_upload_to, validators=[validate_attachment])
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField(default=0)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.PHOTO)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["created_at"]
