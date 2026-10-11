"""
Ijara shartnomasi va unga bog'liq yozuvlar (billing-urmon.uz dan moslab
ko'chirilgan; Invoice/Transaction/Balance ko'chirilmagan — qarzdorlik
`rent_amount - paid_amount`).
"""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.base.models import AbstractBaseModel
from apps.utils.validators import validate_document_file

from .reference import ActivityType, Bolim, District, LandType, PrivilegeType, Region, Renter, Xojalik

ZERO = Decimal("0.00")


class Contract(AbstractBaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Faol"
        INACTIVE = "inactive", "Faol emas"

    renter = models.ForeignKey(Renter, on_delete=models.PROTECT, related_name="contracts", verbose_name="Ijarachi")
    number = models.CharField(max_length=200, unique=True, verbose_name="Tizim raqami")
    contract_number = models.CharField(max_length=200, null=True, blank=True, verbose_name="Shartnoma raqami")
    xojalik = models.ForeignKey(Xojalik, on_delete=models.PROTECT, related_name="contracts", verbose_name="Xo'jalik")
    bolim = models.ForeignKey(Bolim, on_delete=models.SET_NULL, null=True, blank=True, related_name="contracts", verbose_name="Bo'lim")
    region = models.ForeignKey(Region, on_delete=models.PROTECT, null=True, blank=True, related_name="contracts", verbose_name="Viloyat")
    district = models.ForeignKey(District, on_delete=models.PROTECT, null=True, blank=True, related_name="contracts", verbose_name="Tuman")

    contract_date = models.DateField(verbose_name="Shartnoma sanasi")
    expired_date = models.DateField(null=True, blank=True, verbose_name="Tugash sanasi")
    auction_date = models.DateField(null=True, blank=True, verbose_name="Auksion sanasi")
    exemptioned_date = models.DateField(null=True, blank=True, verbose_name="Imtiyoz tugash sanasi")
    canceled_date = models.DateField(null=True, blank=True, verbose_name="Bekor qilingan sana")
    cancel_reason = models.CharField(max_length=1024, null=True, blank=True, verbose_name="Bekor qilish sababi")

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, verbose_name="Holati")

    rent_amount = models.DecimalField(max_digits=22, decimal_places=2, default=ZERO, verbose_name="Jami hisoblangan")
    paid_amount = models.DecimalField(max_digits=22, decimal_places=2, default=ZERO, verbose_name="To'langan")
    penalty_amount = models.DecimalField(max_digits=22, decimal_places=2, default=ZERO, verbose_name="Penya")

    rent_area = models.DecimalField(max_digits=16, decimal_places=2, default=ZERO, verbose_name="Ijara maydoni (ga)")
    cadastral_number = models.CharField(max_length=55, null=True, blank=True, verbose_name="Kadastr raqami")
    is_entity = models.BooleanField(default=False, verbose_name="Yuridik shaxs")
    circle = models.CharField(max_length=255, null=True, blank=True, verbose_name="Aylanma")
    section = models.CharField(max_length=255, null=True, blank=True, verbose_name="Kvartal")
    counter = models.CharField(max_length=255, null=True, blank=True, verbose_name="Kontur")
    massive = models.CharField(max_length=255, null=True, blank=True, verbose_name="Videl / massiv")

    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name="Kenglik")
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name="Uzunlik")
    boundary_geojson = models.JSONField(null=True, blank=True, verbose_name="Yer chegarasi (GeoJSON)")

    class Meta:
        verbose_name = "Ijara shartnomasi"
        verbose_name_plural = "Ijara shartnomalari"
        ordering = ["xojalik__name", "-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["contract_date"]),
        ]

    def __str__(self) -> str:
        return self.contract_number or self.number

    @property
    def debt(self) -> Decimal:
        return (self.rent_amount or ZERO) - (self.paid_amount or ZERO)

    @property
    def days_remaining(self):
        if not self.expired_date:
            return None
        delta = (self.expired_date - timezone.localdate()).days
        return delta if delta > 0 else 0

    @property
    def is_expired(self) -> bool:
        return bool(self.expired_date and timezone.localdate() > self.expired_date)

    @property
    def has_boundary(self) -> bool:
        return bool(self.boundary_geojson)


class ContractYearlyAmount(AbstractBaseModel):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="yearly_amounts")
    year = models.PositiveSmallIntegerField(verbose_name="Yil")
    contract_amount = models.DecimalField(max_digits=22, decimal_places=2, default=ZERO, verbose_name="Shartnoma summasi")
    calculated_amount = models.DecimalField(max_digits=22, decimal_places=2, default=ZERO, verbose_name="Hisoblangan summa")
    paid_amount = models.DecimalField(max_digits=22, decimal_places=2, default=ZERO, verbose_name="To'langan summa")
    penalty_amount = models.DecimalField(max_digits=22, decimal_places=2, default=ZERO, verbose_name="Penya")

    class Meta:
        verbose_name = "Shartnoma yillik summasi"
        verbose_name_plural = "Shartnoma yillik summalari"
        ordering = ["year"]
        constraints = [models.UniqueConstraint(fields=["contract", "year"], name="billing_yearly_contract_year_uniq")]

    def __str__(self) -> str:
        return f"{self.contract_id} — {self.year}"

    @property
    def debt_amount(self) -> Decimal:
        return (self.calculated_amount or ZERO) - (self.paid_amount or ZERO)


def sync_contract_totals(contract_id) -> bool:
    """
    Yillik qatorlari bor shartnomada rent_amount/paid_amount/penalty_amount
    doim ularning yig'indisi. Qatorlar bo'lmasa tegilmaydi (False).
    """
    agg = ContractYearlyAmount.objects.filter(contract_id=contract_id).aggregate(
        rows=models.Count("id"),
        total_calculated=models.Sum("calculated_amount"),
        total_paid=models.Sum("paid_amount"),
        total_penalty=models.Sum("penalty_amount"),
    )
    if not agg["rows"]:
        return False
    Contract.objects.filter(id=contract_id).update(
        rent_amount=agg["total_calculated"] or ZERO,
        paid_amount=agg["total_paid"] or ZERO,
        penalty_amount=agg["total_penalty"] or ZERO,
    )
    return True


class ContractLand(AbstractBaseModel):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="lands")
    type = models.ForeignKey(LandType, on_delete=models.PROTECT, related_name="contract_lands", verbose_name="Yer turi")
    area = models.DecimalField(max_digits=13, decimal_places=2, verbose_name="Maydon (ga)")

    class Meta:
        verbose_name = "Shartnoma yer turi"
        verbose_name_plural = "Shartnoma yer turlari"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.type} — {self.area}"


class ContractActivity(AbstractBaseModel):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="activities")
    type = models.ForeignKey(ActivityType, on_delete=models.PROTECT, related_name="contract_activities", verbose_name="Faoliyat turi")
    area = models.DecimalField(max_digits=13, decimal_places=2, verbose_name="Maydon (ga)")

    class Meta:
        verbose_name = "Shartnoma faoliyat turi"
        verbose_name_plural = "Shartnoma faoliyat turlari"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.type} — {self.area}"


class ContractPrivilege(AbstractBaseModel):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="privileges")
    type = models.ForeignKey(PrivilegeType, on_delete=models.PROTECT, related_name="contract_privileges", verbose_name="Imtiyoz turi")
    area = models.DecimalField(max_digits=13, decimal_places=2, verbose_name="Maydon (ga)")

    class Meta:
        verbose_name = "Shartnoma imtiyozi"
        verbose_name_plural = "Shartnoma imtiyozlari"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.type} — {self.area}"


class ContractAction(AbstractBaseModel):
    """Bajarilgan ishlar: ish o'rinlari va o'z investitsiyasi."""

    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="actions")
    vacancy = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True, verbose_name="Ish o'rinlari")
    own_investment = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True, verbose_name="O'z investitsiyasi")

    class Meta:
        verbose_name = "Bajarilgan ishlar"
        verbose_name_plural = "Bajarilgan ishlar"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.contract_id} — ishlar"


class ContractActionProduct(AbstractBaseModel):
    action = models.ForeignKey(ContractAction, on_delete=models.CASCADE, related_name="products")
    product_export = models.CharField(max_length=120, null=True, blank=True, verbose_name="Mahsulot turi")
    product_amount = models.CharField(max_length=120, null=True, blank=True, verbose_name="Mahsulot miqdori")
    export_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True, verbose_name="Eksport hajmi")

    class Meta:
        verbose_name = "Eksport mahsuloti"
        verbose_name_plural = "Eksport mahsulotlari"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return self.product_export or str(self.id)


class ContractFile(AbstractBaseModel):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="files", verbose_name="Shartnoma")
    # max_length=500: eski billing'dan ko'chirilgan uzun fayl yo'llari (documents/billing/contracts/legacy/...)
    file = models.FileField(
        upload_to="documents/billing/contracts/%Y/%m/", max_length=500, validators=[validate_document_file], verbose_name="Fayl",
    )
    description = models.CharField(max_length=500, null=True, blank=True, verbose_name="Izoh")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="billing_uploaded_files", verbose_name="Yuklagan",
    )

    class Meta:
        verbose_name = "Shartnoma fayli"
        verbose_name_plural = "Shartnoma fayllari"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.contract} — {self.file.name.rsplit('/', 1)[-1]}"


class ContractHistory(AbstractBaseModel):
    class Reason(models.TextChoices):
        CREATED = "created", "Yaratildi"
        UPDATED = "updated", "Yangilandi"
        STATUS_CHANGED = "status_changed", "Holati o'zgardi"
        RENTER_CHANGED = "renter_changed", "Ijarachi o'zgardi"
        YEARLY_UPDATED = "yearly_updated", "Yillik summalar yangilandi"
        FILE_ADDED = "file_added", "Fayl qo'shildi"
        FILE_DELETED = "file_deleted", "Fayl o'chirildi"
        IMPORTED = "imported", "Excel'dan import qilindi"

    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="history")
    executor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="billing_contract_history", verbose_name="Bajaruvchi",
    )
    reason = models.CharField(max_length=20, choices=Reason.choices, verbose_name="Sabab")
    data = models.JSONField(default=dict, blank=True, verbose_name="O'zgarishlar (old/new)")

    class Meta:
        verbose_name = "Shartnoma tarixi"
        verbose_name_plural = "Shartnoma tarixi"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.contract_id} — {self.reason}"
