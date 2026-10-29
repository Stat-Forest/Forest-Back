"""
Yetkazib beruvchi ombori — ledger (TZ §9, §22.1, §22.3).

Qoldiq alohida ustunda saqlanmaydi: `StockMovement` (status=posted) yig'indisi =
hisob qoldig'i. Har o'zgarish hujjatli harakat: boshlang'ich qoldiq, kirim,
ijroga qabulda ajratish (−), bekor qilishda tiklash (+), haqiqiy qaytarish (+),
teskari operatsiya (± `reversal_of`, imzolash huquqi bor a'zo tasdiqlaydi).
O'rmon xo'jaligida qoldiq manfiy bo'lishi mumkin (ta'minlanmagan ehtiyoj).
"""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.base.models import AbstractBaseModel
from apps.yashil.models.catalog import CatalogItem
from apps.yashil.models.membership import YashilMembership
from apps.yashil.models.orders import Order, OrderLine, validate_attachment


class Warehouse(AbstractBaseModel):
    organization = models.ForeignKey("general.Organization", on_delete=models.PROTECT, related_name="yashil_warehouses")
    name = models.CharField(max_length=200, default="Асосий омбор", verbose_name="Nomi")
    is_default = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Ombor"
        verbose_name_plural = "Omborlar"
        ordering = ["organization__name", "-is_default", "name"]
        constraints = [models.UniqueConstraint(fields=["organization", "name"], name="yashil_warehouse_name_uniq")]

    def __str__(self):
        return f"{self.organization} — {self.name}"


def stock_file_upload_to(instance, filename):
    return f"documents/yashil/stock/{instance.warehouse_id}/{filename}"


class StockMovement(AbstractBaseModel):
    class Kind(models.TextChoices):
        OPENING = "opening", "Boshlang'ich qoldiq"
        RECEIPT = "receipt", "Kirim"
        ALLOCATE = "allocate", "Ijroga qabulda ajratish"
        RELEASE = "release", "Ajratishni tiklash (bekor)"
        RETURN_IN = "return_in", "Haqiqiy qaytarish"
        REVERSAL = "reversal", "Teskari operatsiya"

    class Status(models.TextChoices):
        POSTED = "posted", "Hisobga o'tgan"
        PENDING = "pending_approval", "Tasdiq kutilmoqda"
        REJECTED = "rejected", "Rad etilgan"

    REVERSIBLE_KINDS = (Kind.OPENING, Kind.RECEIPT, Kind.RETURN_IN)

    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="movements")
    catalog_item = models.ForeignKey(CatalogItem, on_delete=models.PROTECT, related_name="stock_movements")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    qty = models.DecimalField(max_digits=18, decimal_places=4, help_text="Ishorali: ajratish manfiy")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.POSTED, db_index=True)
    acceptance = models.ForeignKey("yashil.Acceptance", on_delete=models.PROTECT, null=True, blank=True, related_name="movements")
    order_line = models.ForeignKey(OrderLine, on_delete=models.PROTECT, null=True, blank=True, related_name="stock_movements")
    doc_number = models.CharField(max_length=100, blank=True, verbose_name="Hujjat raqami")
    doc_date = models.DateField(null=True, blank=True, verbose_name="Hujjat sanasi")
    note = models.CharField(max_length=1000, blank=True, verbose_name="Asos / izoh")
    file = models.FileField(upload_to=stock_file_upload_to, null=True, blank=True, validators=[validate_attachment])
    reversal_of = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="reversals")
    requested_by_membership = models.ForeignKey(YashilMembership, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=1000, blank=True)

    class Meta:
        verbose_name = "Ombor harakati"
        verbose_name_plural = "Ombor harakatlari"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["warehouse", "catalog_item"]), models.Index(fields=["warehouse", "doc_number"])]
        constraints = [
            models.UniqueConstraint(fields=["acceptance", "order_line"], condition=Q(kind="allocate"), name="yashil_stock_allocate_uniq"),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {self.qty} {self.catalog_item.code}"


class Acceptance(AbstractBaseModel):
    """Ijroga qabul hodisasi — buyurtmaga bitta (takror qabuldan himoya, TZ §9.2)."""

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="acceptance")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="acceptances")
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    accepted_by_membership = models.ForeignKey(YashilMembership, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    accepted_on = models.DateField()
    delivery_due = models.DateField()
    executor_name = models.CharField(max_length=300, blank=True)
    result = models.JSONField(default=dict, blank=True, help_text="Qatorlar bo'yicha ajratish natijasi (yetishmovchilik bilan)")

    class Meta:
        verbose_name = "Ijroga qabul"
        verbose_name_plural = "Ijroga qabullar"
        ordering = ["-created_at"]


class ServiceAllocation(AbstractBaseModel):
    """DM xizmat quvvati sarfi: oy bo'yicha quvvatdan buyurtma qatoriga ajratilgan hajm."""

    organization = models.ForeignKey("general.Organization", on_delete=models.PROTECT, related_name="yashil_service_allocations")
    catalog_item = models.ForeignKey(CatalogItem, on_delete=models.PROTECT, related_name="service_allocations")
    period = models.CharField(max_length=7, verbose_name="Davr (YYYY-MM)")
    acceptance = models.ForeignKey(Acceptance, on_delete=models.CASCADE, related_name="service_allocations")
    order_line = models.OneToOneField(OrderLine, on_delete=models.PROTECT, related_name="service_allocation")
    qty = models.DecimalField(max_digits=18, decimal_places=4)

    class Meta:
        verbose_name = "Xizmat quvvati sarfi"
        verbose_name_plural = "Xizmat quvvati sarflari"
        indexes = [models.Index(fields=["organization", "catalog_item", "period"])]


ZERO = Decimal("0")
