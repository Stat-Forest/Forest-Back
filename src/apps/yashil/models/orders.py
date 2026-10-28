"""
Buyurtma oqimi (TZ §4–§7, §16, §20): buyurtma, qatorlar, o'zgarmas versiyalar,
ilovalar, ko'rib chiqish segmentlari (3 ish kuni), jarayon jurnali.

`Order` — joriy holat; har imzoli yuborish `OrderVersion.snapshot` da muzlaydi.
Raqam `YM-YYYY-NNNNNN` birinchi yuborishda beriladi (services/numbering.py).
"""
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.base.models import AbstractBaseModel
from apps.utils.validators import FileTypeValidator
from apps.yashil.models.reference import Mahalla, ObjectType, Season, SupplierProfile, UnionUnit
from apps.yashil.models.catalog import CatalogItem
from apps.yashil.models.membership import YashilMembership


class OrderState(models.TextChoices):
    DRAFT = "draft", "Qoralama"
    UNION_NEW = "union_new", "Uyushmada yangi"
    UNION_REVIEW = "union_review", "Uyushma ko'rib chiqmoqda"
    RETURNED = "returned", "Mahallaga qaytarilgan"
    SUPPLIER_NEW = "supplier_new", "Yetkazib beruvchida yangi"
    SUPPLIER_REVIEW = "supplier_review", "Yetkazib beruvchi ko'rib chiqmoqda"
    EXECUTION = "execution", "Ijroda"
    PARTIAL = "partial", "Qisman bajarilgan"
    CLOSED = "closed", "Bajarilgan"
    CANCELLED = "cancelled", "Bekor qilingan"


# Kirill nomlari (interfeys va hujjat uchun; TZ §7 jadvali)
STATE_LABELS_CYR = {
    OrderState.DRAFT: "Қоралама",
    OrderState.UNION_NEW: "Уюшмада янги",
    OrderState.UNION_REVIEW: "Уюшма кўриб чиқмоқда",
    OrderState.RETURNED: "Маҳаллага қайтарилган",
    OrderState.SUPPLIER_NEW: "Етказиб берувчида янги",
    OrderState.SUPPLIER_REVIEW: "Етказиб берувчи кўриб чиқмоқда",
    OrderState.EXECUTION: "Ижрода",
    OrderState.PARTIAL: "Қисман бажарилган",
    OrderState.CLOSED: "Бажарилган",
    OrderState.CANCELLED: "Бекор қилинган",
}

REVIEW_STATES = {OrderState.UNION_NEW, OrderState.UNION_REVIEW, OrderState.SUPPLIER_NEW, OrderState.SUPPLIER_REVIEW}
EDITABLE_STATES = {OrderState.DRAFT, OrderState.RETURNED}
DELIVERY_STATES = {OrderState.EXECUTION, OrderState.PARTIAL}
FINAL_STATES = {OrderState.CLOSED, OrderState.CANCELLED}


class ReturnReason(models.TextChoices):
    ADDRESS = "address", "Manzil / joylashuv"
    LINES = "lines", "Mahsulot yoki miqdor"
    SUPPLIER = "supplier", "Yetkazib beruvchi"
    DOCUMENTS = "documents", "Hujjatlar / ilovalar"
    NORMS = "norms", "Meyorlar"
    OTHER = "other", "Boshqa"


class OrderSequence(models.Model):
    """Yil bo'yicha raqam hisoblagichi (select_for_update bilan)."""

    year = models.PositiveSmallIntegerField(unique=True)
    last = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Buyurtma raqami hisoblagichi"
        verbose_name_plural = "Buyurtma raqami hisoblagichlari"


class Order(AbstractBaseModel):
    number = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="Raqami")
    mahalla = models.ForeignKey(Mahalla, on_delete=models.PROTECT, related_name="orders")
    route = models.CharField(max_length=10, choices=SupplierProfile.SupplierType.choices, verbose_name="Yo'nalish")
    supplier_org = models.ForeignKey("general.Organization", on_delete=models.PROTECT, related_name="yashil_orders", verbose_name="Yetkazib beruvchi")
    union_unit = models.ForeignKey(UnionUnit, on_delete=models.PROTECT, null=True, blank=True, related_name="orders")
    state = models.CharField(max_length=20, choices=OrderState.choices, default=OrderState.DRAFT, db_index=True)
    version_no = models.PositiveIntegerField(default=1)

    title = models.CharField(max_length=200, blank=True, verbose_name="Buyurtma nomi")
    object_type = models.ForeignKey(ObjectType, on_delete=models.PROTECT, null=True, blank=True, related_name="orders")
    object_note = models.CharField(max_length=500, blank=True)
    season = models.ForeignKey(Season, on_delete=models.PROTECT, null=True, blank=True, related_name="orders")
    address = models.CharField(max_length=500, blank=True, verbose_name="Manzil")
    lat = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    lon = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    polygon = models.JSONField(null=True, blank=True, verbose_name="Poligon (GeoJSON)")
    area_ha = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, verbose_name="Maydon, ga")
    area_calc_ha = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    area_note = models.CharField(max_length=500, blank=True)
    water_source = models.CharField(max_length=300, blank=True)
    contact_person = models.CharField(max_length=300, blank=True)
    extra_info = models.TextField(max_length=4000, blank=True)
    base_seedlings = models.PositiveIntegerField(null=True, blank=True, verbose_name="Asos ko'chatlar soni")
    problem_note = models.TextField(max_length=4000, blank=True, verbose_name="Xizmat uchun muammo tavsifi")
    linked_order = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="repeat_orders")
    repeat_reason = models.CharField(max_length=1000, blank=True)

    created_by_membership = models.ForeignKey(YashilMembership, on_delete=models.PROTECT, related_name="created_orders")
    first_submitted_at = models.DateTimeField(null=True, blank=True)
    last_submitted_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_on = models.DateField(null=True, blank=True, help_text="Asia/Tashkent sanasi")
    delivery_due = models.DateField(null=True, blank=True)
    executor_name = models.CharField(max_length=300, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True, help_text="Bajarilgan yoki bekor qilingan vaqt")
    current_version = models.ForeignKey("yashil.OrderVersion", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["mahalla", "state"]),
            models.Index(fields=["supplier_org", "state"]),
            models.Index(fields=["union_unit", "state"]),
        ]

    def review_segments_as_tuples(self):
        return [(str(s.started_on), str(s.ended_on) if s.ended_on else None) for s in self.review_segments.order_by("started_on")]

    def review_segments_as_tuples_dates(self):
        return [(s.started_on, s.ended_on) for s in self.review_segments.order_by("started_on")]

    @property
    def display_number(self) -> str:
        return self.number or f"Қоралама {str(self.id)[:8]}"

    def __str__(self):
        return self.display_number


class OrderLine(AbstractBaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    catalog_item = models.ForeignKey(CatalogItem, on_delete=models.PROTECT, related_name="order_lines")
    qty = models.DecimalField(max_digits=18, decimal_places=4, validators=[MinValueValidator(0)])
    attrs_note = models.CharField(max_length=300, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Buyurtma qatori"
        verbose_name_plural = "Buyurtma qatorlari"
        ordering = ["position", "created_at"]
        constraints = [models.UniqueConstraint(fields=["order", "catalog_item"], name="yashil_orderline_item_uniq")]


class OrderVersion(AbstractBaseModel):
    """Imzolash paytida muzlatilgan nusxa (TZ §11.2)."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="versions")
    version_no = models.PositiveIntegerField()
    snapshot = models.JSONField()
    document_version = models.ForeignKey("yashil.DocumentVersion", on_delete=models.SET_NULL, null=True, blank=True, related_name="order_versions")
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    superseded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-version_no"]
        constraints = [models.UniqueConstraint(fields=["order", "version_no"], name="yashil_orderversion_uniq")]


ATTACHMENT_TYPES = {
    ".pdf": (b"%PDF",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG",),
}
ATTACHMENT_MAX_SIZE = 10 * 1024 * 1024
ATTACHMENT_TOTAL_MAX = 50 * 1024 * 1024
validate_attachment = FileTypeValidator(ATTACHMENT_TYPES, max_size=ATTACHMENT_MAX_SIZE)


def attachment_upload_to(instance, filename):
    return f"documents/yashil/orders/{instance.order_id}/{filename}"


class OrderAttachment(AbstractBaseModel):
    class Kind(models.TextChoices):
        PHOTO = "photo", "Foto"
        SCHEME = "scheme", "Sxema"
        PDF = "pdf", "PDF"
        OTHER = "other", "Boshqa"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="attachments")
    version_no = models.PositiveIntegerField(default=1)
    file = models.FileField(upload_to=attachment_upload_to, validators=[validate_attachment])
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField(default=0)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.OTHER)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["created_at"]


class ReviewSegment(models.Model):
    """3 ish kuni hisoblanadigan davr: yuborish → mahallaga qaytarish/ijroga qabul."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="review_segments")
    started_on = models.DateField()
    ended_on = models.DateField(null=True, blank=True)
    ended_reason = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["started_on"]


class OrderEvent(models.Model):
    """Jarayon jurnali — o'chirilmaydi (TZ §7.1, §17.2)."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    action = models.CharField(max_length=40)
    from_state = models.CharField(max_length=20, blank=True)
    to_state = models.CharField(max_length=20, blank=True)
    actor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    actor_membership = models.ForeignKey(YashilMembership, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    actor_label = models.CharField(max_length=300, blank=True, help_text="Tashkilot/kabinet nomi (o'zgarmas)")
    comment = models.TextField(blank=True)
    reason_code = models.CharField(max_length=20, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["order", "created_at"])]
