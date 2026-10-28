"""Katalog, meyorlar, xizmat quvvati (TZ §3.2, §5.3; javoblar В1–В6)."""
from django.core.exceptions import ValidationError
from django.db import models

from apps.yashil.models._base import ValidatedModel
from apps.yashil.models.reference import SupplierProfile
from apps.yashil.services.units import UNIT_CHOICES, precision_for


class CatalogItem(ValidatedModel):
    class ItemType(models.TextChoices):
        GOODS = "goods", "Tovar"
        SERVICE = "service", "Xizmat"

    class Category(models.TextChoices):
        SEEDLING = "seedling", "Ko'chat"
        MULCH = "mulch", "Mulcha"
        FERTILIZER = "fertilizer", "Organik o'g'it / biogumus"
        EQUIPMENT = "equipment", "Asbob-uskuna"
        IRRIGATION = "irrigation", "Sug'orish vositalari"
        PROTECTION_SERVICE = "protection_service", "Himoya xizmati"

    FOREST_CATEGORIES = {Category.SEEDLING, Category.MULCH}
    SERVICE_CATEGORIES = {Category.PROTECTION_SERVICE}

    code = models.CharField(max_length=40, unique=True, verbose_name="Kodi")
    name_cyr = models.CharField(max_length=300, verbose_name="Nomi (kirill)")
    name_lat = models.CharField(max_length=300, verbose_name="Nomi (lotin)")
    supplier_type = models.CharField(max_length=10, choices=SupplierProfile.SupplierType.choices, verbose_name="Yo'nalish")
    item_type = models.CharField(max_length=10, choices=ItemType.choices, default=ItemType.GOODS)
    category = models.CharField(max_length=30, choices=Category.choices)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, verbose_name="O'lchov birligi")
    precision = models.PositiveSmallIntegerField(default=0, editable=False, verbose_name="O'nlik xona")
    attributes = models.JSONField(default=dict, blank=True, verbose_name="Xususiyatlar", help_text="Masalan: tur, yosh, bo'y, model, sig'im")
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(null=True, blank=True)
    version = models.PositiveSmallIntegerField(default=1)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Katalog pozitsiyasi"
        verbose_name_plural = "Katalog"
        ordering = ["supplier_type", "order", "code"]

    def clean(self):
        super().clean()
        if self.unit:
            self.precision = precision_for(self.unit)
        if self.supplier_type == SupplierProfile.SupplierType.FOREST and self.category not in self.FOREST_CATEGORIES:
            raise ValidationError({"category": "O'rmon xo'jaligi katalogida faqat ko'chat va mulcha bo'ladi."})
        if self.category in self.SERVICE_CATEGORIES and self.item_type != self.ItemType.SERVICE:
            raise ValidationError({"item_type": "Himoya xizmati — xizmat turi."})
        if self.item_type == self.ItemType.SERVICE and self.supplier_type != SupplierProfile.SupplierType.DM:
            raise ValidationError({"supplier_type": "Xizmatlar faqat DM yo'nalishida."})

    def __str__(self):
        return f"{self.code} — {self.name_lat}"


class NormRule(ValidatedModel):
    """Versiyali meyor (masalan biogumus 5 kg/tup). Imzolangan hujjatlar o'zgarmaydi."""

    code = models.CharField(max_length=60, verbose_name="Kodi", help_text="Masalan: fertilizer_per_tup_kg")
    description = models.CharField(max_length=500)
    applies_to_category = models.CharField(max_length=30, choices=CatalogItem.Category.choices, blank=True)
    applies_to_item = models.ForeignKey(CatalogItem, on_delete=models.PROTECT, null=True, blank=True, related_name="norm_rules")
    params = models.JSONField(default=dict, verbose_name="Parametrlar", help_text='{"max_per_tup": 5}')
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    version = models.PositiveSmallIntegerField(default=1)
    approved_ref = models.CharField(max_length=300, blank=True, verbose_name="Tasdiqlagan hujjat")

    class Meta:
        verbose_name = "Meyor"
        verbose_name_plural = "Meyorlar"
        ordering = ["code", "-effective_from"]
        constraints = [models.UniqueConstraint(fields=["code", "version"], name="yashil_norm_code_version_uniq")]

    def clean(self):
        super().clean()
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError({"effective_to": "Tugash sanasi boshlanishdan oldin."})

    def __str__(self):
        return f"{self.code} v{self.version}"


class ServiceCapacity(ValidatedModel):
    """DM xizmat quvvati: tashkilot × pozitsiya × oy (javob В5)."""

    organization = models.ForeignKey("general.Organization", on_delete=models.CASCADE, related_name="yashil_capacities")
    catalog_item = models.ForeignKey(CatalogItem, on_delete=models.PROTECT, related_name="capacities")
    period = models.CharField(max_length=7, verbose_name="Davr (YYYY-MM)")
    capacity = models.DecimalField(max_digits=18, decimal_places=4)

    class Meta:
        verbose_name = "Xizmat quvvati"
        verbose_name_plural = "Xizmat quvvatlari"
        constraints = [models.UniqueConstraint(fields=["organization", "catalog_item", "period"], name="yashil_capacity_uniq")]

    def clean(self):
        super().clean()
        if self.catalog_item_id and self.catalog_item.item_type != CatalogItem.ItemType.SERVICE:
            raise ValidationError({"catalog_item": "Quvvat faqat xizmat pozitsiyasi uchun."})
        if self.period and (len(self.period) != 7 or self.period[4] != "-" or not self.period.replace("-", "").isdigit()):
            raise ValidationError({"period": "Davr YYYY-MM ko'rinishida."})

    def __str__(self):
        return f"{self.organization} / {self.catalog_item.code} / {self.period}"
