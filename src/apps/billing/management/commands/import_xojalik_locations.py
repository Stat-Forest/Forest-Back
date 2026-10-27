"""
GIS xo'jalik hududlari va konturlarini `fixtures/xojalik_locations.json.gz`
dan yuklaydi (billing'dan moslab: `region_id` -> Region.billing_id, xo'jalik
nomi bo'yicha `Xojalik` bog'lanadi). Qayta ishga tushirish xavfsiz;
`--if-empty` — jadval bo'sh bo'lsa faqat (entrypoint uchun, 8 MB fixture
har deploy'da qayta o'qilmasin).
"""
import gzip
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.billing.models import Region, Xojalik, XojalikKontur, XojalikLocation
from apps.billing.services.geo import build_outline

DEFAULT_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "xojalik_locations.json.gz"
LOCATION_FIELDS = ("latitude", "longitude", "bounds", "boundary_geojson", "area_ga", "parcel_count")
KONTUR_FIELDS = ("kontur_raqami", "raqami_num", "latitude", "longitude", "bounds", "area_ga", "attributes", "geojson")


def fingerprint(region_id, parcel_count, area_ga):
    return (region_id, parcel_count, round(float(area_ga or 0), 2))


class Command(BaseCommand):
    help = "Xo'jaliklar joylashuvi va konturlarini fixture'dan import qiladi (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--source", default=str(DEFAULT_FIXTURE), help="xojalik_locations.json(.gz) yo'li")
        parser.add_argument("--name", action="append", default=[], help="Faqat shu nomli xo'jalik(lar)")
        parser.add_argument("--dry-run", action="store_true", help="Hech narsa saqlamaydi")
        parser.add_argument("--if-empty", action="store_true", help="XojalikLocation jadvali bo'sh bo'lsa faqat")

    def handle(self, *args, **options):
        if options["if_empty"] and XojalikLocation.objects.exists():
            self.stdout.write("XojalikLocation jadvali bo'sh emas — import o'tkazib yuborildi (--if-empty).")
            return

        source = Path(options["source"])
        if not source.exists():
            self.stdout.write(self.style.ERROR(f"Fayl topilmadi: {source}"))
            return
        opener = gzip.open if source.suffix == ".gz" else open
        with opener(source, "rt", encoding="utf-8") as fh:
            records = json.load(fh)
        self.stdout.write(f"{len(records)} ta yozuv o'qildi: {source.name}")

        if options["name"]:
            wanted = set(options["name"])
            records = [r for r in records if r.get("name") in wanted]
            missing = wanted - {r["name"] for r in records}
            if missing:
                self.stdout.write(self.style.ERROR(f"Fixture'da topilmadi: {', '.join(sorted(missing))}"))

        self.stats = dict(created=0, updated=0, skipped=0, linked=0, k_created=0, k_updated=0, k_deleted=0)
        self.regions = {r.billing_id: r for r in Region.objects.exclude(billing_id__isnull=True)}
        with transaction.atomic():
            for row in records:
                self.import_row(row)
            if options["dry_run"]:
                transaction.set_rollback(True)

        s = self.stats
        self.stdout.write(self.style.SUCCESS(
            f"{'DRY RUN — ' if options['dry_run'] else ''}Xo'jaliklar: yaratildi {s['created']}, yangilandi {s['updated']}, "
            f"bog'landi {s['linked']}, o'tkazib yuborildi {s['skipped']}; konturlar: yaratildi {s['k_created']}, "
            f"yangilandi {s['k_updated']}, o'chirildi {s['k_deleted']}"
        ))

    def find_existing(self, name, region, xojalik, row):
        by_name = list(XojalikLocation.objects.filter(name=name, region=region)[:2])
        if len(by_name) == 1:
            return by_name[0], "nom"
        if len(by_name) > 1:
            return None, f"'{name}' nomli {len(by_name)}+ ta yozuv bor"
        if xojalik:
            by_xojalik = list(XojalikLocation.objects.filter(xojalik=xojalik)[:2])
            if len(by_xojalik) == 1:
                return by_xojalik[0], "xo'jalik"
        key = fingerprint(region.id, row.get("parcel_count"), row.get("area_ga"))
        by_fp = [
            x for x in XojalikLocation.objects.filter(region=region, parcel_count=row.get("parcel_count"))
            if fingerprint(x.region_id, x.parcel_count, x.area_ga) == key
        ]
        if len(by_fp) == 1:
            return by_fp[0], "kontur soni+maydon"
        if len(by_fp) > 1:
            return None, f"kontur soni+maydon bo'yicha {len(by_fp)} ta yozuv mos keldi"
        return None, None

    def import_row(self, row):
        name = row.get("name")
        region = self.regions.get(row.get("region_id"))
        if not name or region is None:
            self.stats["skipped"] += 1
            self.stdout.write(self.style.ERROR(f"O'tkazib yuborildi (nom/viloyat topilmadi): {name} / region_id={row.get('region_id')}"))
            return

        xojaliklar = list(Xojalik.objects.filter(name=name, region=region)[:2])
        xojalik = xojaliklar[0] if len(xojaliklar) == 1 else None

        obj, how = self.find_existing(name, region, xojalik, row)
        if obj is None and how:
            self.stats["skipped"] += 1
            self.stdout.write(self.style.ERROR(f"O'tkazib yuborildi: {region.name} - {name}: {how}"))
            return

        defaults = {f: row.get(f) for f in LOCATION_FIELDS}
        defaults["outline_geojson"] = build_outline(defaults.get("boundary_geojson"))
        is_new = obj is None
        if is_new:
            obj = XojalikLocation.objects.create(name=name, region=region, **defaults)
            self.stats["created"] += 1
        else:
            for field, value in defaults.items():
                setattr(obj, field, value)
            obj.save(update_fields=[*LOCATION_FIELDS, "outline_geojson", "updated_at"])
            self.stats["updated"] += 1

        if not obj.xojalik_id and xojalik:
            obj.xojalik = xojalik
            obj.save(update_fields=["xojalik", "updated_at"])
            self.stats["linked"] += 1

        self.import_konturlar(obj, row.get("konturlar") or [], is_new)

    @staticmethod
    def _kontur_values(k):
        values = {f: k.get(f) for f in KONTUR_FIELDS}
        values["kontur_raqami"] = values["kontur_raqami"] or ""
        return values

    def import_konturlar(self, obj, konturlar, is_new):
        if is_new:
            # Yangi xo'jalik: 40 mingga yaqin kontur bitta so'rovlar paketida (birinchi deploy tez bo'lsin)
            XojalikKontur.objects.bulk_create(
                [XojalikKontur(xojalik_location=obj, seq=k.get("seq"), **self._kontur_values(k)) for k in konturlar],
                batch_size=1000,
            )
            self.stats["k_created"] += len(konturlar)
            return
        seqs = []
        for k in konturlar:
            seqs.append(k.get("seq"))
            _, created = XojalikKontur.objects.update_or_create(
                xojalik_location=obj, seq=k.get("seq"), defaults=self._kontur_values(k),
            )
            self.stats["k_created" if created else "k_updated"] += 1
        if seqs:
            deleted, _ = obj.konturlar.exclude(seq__in=seqs).delete()
            self.stats["k_deleted"] += deleted
