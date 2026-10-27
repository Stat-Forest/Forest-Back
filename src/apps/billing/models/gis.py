"""
GIS: xo'jaliklar hududi va konturlari (KMZ'dan olingan, fixture orqali
`import_xojalik_locations` buyrug'i bilan yuklanadi).
"""
from django.db import models

from apps.base.models import AbstractBaseModel

from .reference import Region, Xojalik


class XojalikLocation(AbstractBaseModel):
    name = models.CharField(max_length=255, verbose_name="Xo'jalik nomi")
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="xojalik_locations", verbose_name="Viloyat")
    xojalik = models.ForeignKey(
        Xojalik, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="locations", verbose_name="Mos xo'jalik (billing)",
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=7, verbose_name="Kenglik")
    longitude = models.DecimalField(max_digits=10, decimal_places=7, verbose_name="Uzunlik")
    bounds = models.JSONField(null=True, blank=True, verbose_name="Chegara maydoni", help_text="[[south, west], [north, east]]")
    boundary_geojson = models.JSONField(null=True, blank=True, verbose_name="Konturlar (GeoJSON)")
    outline_geojson = models.JSONField(
        null=True, blank=True, editable=False, verbose_name="Ixcham tashqi chegara (GeoJSON)",
        help_text="boundary_geojson'dan (services.geo.build_outline) — landing xaritasi uchun",
    )
    area_ga = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Umumiy maydon (ga)")
    parcel_count = models.IntegerField(null=True, blank=True, verbose_name="Konturlar soni")

    class Meta:
        verbose_name = "Xo'jalik joylashuvi"
        verbose_name_plural = "Xo'jaliklar joylashuvi"
        ordering = ["region__code", "name"]

    def __str__(self) -> str:
        return self.name


class XojalikKontur(AbstractBaseModel):
    xojalik_location = models.ForeignKey(
        XojalikLocation, on_delete=models.CASCADE, related_name="konturlar", verbose_name="Xo'jalik",
    )
    seq = models.IntegerField(verbose_name="KMZ dagi tartib raqami")
    kontur_raqami = models.CharField(max_length=50, blank=True, verbose_name="Kontur raqami")
    raqami_num = models.IntegerField(null=True, blank=True, verbose_name="Kontur raqami (son)")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, verbose_name="Kenglik")
    longitude = models.DecimalField(max_digits=10, decimal_places=7, verbose_name="Uzunlik")
    bounds = models.JSONField(null=True, blank=True, verbose_name="Chegara maydoni")
    area_ga = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Maydon (ga)")
    attributes = models.JSONField(null=True, blank=True, verbose_name="Qo'shimcha atributlar")
    geojson = models.JSONField(null=True, blank=True, verbose_name="Kontur geometriyasi (GeoJSON)")

    class Meta:
        verbose_name = "Xo'jalik konturi"
        verbose_name_plural = "Xo'jalik konturlari"
        ordering = ["xojalik_location", "raqami_num", "seq"]
        constraints = [models.UniqueConstraint(fields=["xojalik_location", "seq"], name="billing_kontur_location_seq_uniq")]

    def __str__(self) -> str:
        return f"{self.xojalik_location.name} - {self.kontur_raqami or self.seq}"
