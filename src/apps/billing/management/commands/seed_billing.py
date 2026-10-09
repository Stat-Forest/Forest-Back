"""
Billing ma'lumotnomasini (viloyat, tuman, xo'jalik, bo'lim, turlar)
`fixtures/billing_reference.json` dan yuklaydi. Idempotent (update_or_create),
entrypoint'da har deploy'da ishlaydi.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.billing.models import ActivityType, Bolim, District, LandType, PrivilegeType, Region, Xojalik
from apps.billing.services.territory import normalize_district_name, normalize_region_name

DEFAULT_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "billing_reference.json"


def _blank_to_none(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


class Command(BaseCommand):
    help = "Ijara billing ma'lumotnomasini (viloyat/tuman/xo'jalik/bo'lim/turlar) fixture'dan yuklaydi (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--source", default=str(DEFAULT_FIXTURE), help="billing_reference.json yo'li")

    def handle(self, *args, **options):
        source = Path(options["source"])
        with source.open(encoding="utf-8") as fh:
            data = json.load(fh)

        stats = {}
        with transaction.atomic():
            stats["regions"] = self.seed_regions(data.get("regions", []))
            stats["districts"] = self.seed_districts(data.get("districts", []))
            stats["xojaliklar"] = self.seed_xojaliklar(data.get("xojaliklar", []))
            stats["bolimlar"] = self.seed_bolimlar(data.get("bolimlar", []))
            stats["land_types"] = self.seed_types(LandType, data.get("land_types", []))
            stats["activity_types"] = self.seed_types(ActivityType, data.get("activity_types", []))
            stats["privilege_types"] = self.seed_types(PrivilegeType, data.get("privilege_types", []), with_month=True)

        for name, (created, updated) in stats.items():
            self.stdout.write(f"{name}: yaratildi {created}, yangilandi {updated}")
        self.stdout.write(self.style.SUCCESS("seed_billing yakunlandi"))

    @staticmethod
    def _count(created_flag, counter):
        counter[0 if created_flag else 1] += 1

    def seed_regions(self, rows):
        """
        Mavjud viloyat billing_id, nomi yoki eski kodi bo'yicha topiladi va kodi
        MҲОБТ kodiga yangilanadi (eski qisqa kodlardan o'tish dublikat yaratmaydi).
        """
        counter = [0, 0]
        existing = list(Region.objects.all())
        for row in rows:
            code = str(row["code"]).strip()
            name = row["name"].strip()
            old_code = str(row.get("old_code") or "").strip()
            norm = normalize_region_name(name)
            region = (
                next((r for r in existing if r.code == code), None)
                or next((r for r in existing if row.get("billing_id") and r.billing_id == row.get("billing_id")), None)
                or next((r for r in existing if normalize_region_name(r.name) == norm), None)
                or next((r for r in existing if old_code and r.code == old_code), None)
            )
            if region is None:
                region = Region.objects.create(code=code, name=name, billing_id=row.get("billing_id"))
                existing.append(region)
                counter[0] += 1
                continue
            region.code, region.name = code, name
            if row.get("billing_id"):
                region.billing_id = row["billing_id"]
            region.save(update_fields=["code", "name", "billing_id", "updated_at"])
            counter[1] += 1
        return tuple(counter)

    def seed_districts(self, rows):
        """Tuman (viloyat, kod) yoki (viloyat, normallashgan nom) bo'yicha topilib yangilanadi."""
        counter = [0, 0]
        regions = {r.code: r for r in Region.objects.all()}
        by_region: dict = {}
        for district in District.objects.all():
            by_region.setdefault(district.region_id, []).append(district)
        for row in rows:
            region = regions.get(str(row["region_code"]).strip())
            if region is None:
                self.stdout.write(self.style.WARNING(f"Tuman o'tkazib yuborildi (viloyat yo'q): {row}"))
                continue
            code, name = str(row["code"]).strip(), row["name"].strip()
            norm = normalize_district_name(name)
            pool = by_region.setdefault(region.id, [])
            district = next((d for d in pool if d.code == code), None) or next(
                (d for d in pool if normalize_district_name(d.name) == norm), None
            )
            if district is None:
                pool.append(District.objects.create(region=region, code=code, name=name))
                counter[0] += 1
                continue
            if (district.code, district.name) != (code, name):
                district.code, district.name = code, name
                district.save(update_fields=["code", "name", "updated_at"])
            counter[1] += 1
        return tuple(counter)

    def seed_xojaliklar(self, rows):
        counter = [0, 0]
        regions = {r.code: r for r in Region.objects.all()}
        for row in rows:
            region = regions.get(str(row["region_code"]).strip())
            if region is None:
                self.stdout.write(self.style.WARNING(f"Xo'jalik o'tkazib yuborildi (viloyat yo'q): {row['name']}"))
                continue
            _, created = Xojalik.objects.update_or_create(
                name=row["name"].strip(),
                defaults={
                    "region": region,
                    "code": _blank_to_none(row.get("code")),
                    "inn": _blank_to_none(row.get("inn")),
                    "account_detail": _blank_to_none(row.get("account_detail")),
                },
            )
            self._count(created, counter)
        return tuple(counter)

    def seed_bolimlar(self, rows):
        counter = [0, 0]
        xojaliklar = {x.name: x for x in Xojalik.objects.all()}
        for row in rows:
            xojalik = xojaliklar.get(row["xojalik_name"].strip())
            if xojalik is None:
                self.stdout.write(self.style.WARNING(f"Bo'lim o'tkazib yuborildi (xo'jalik yo'q): {row}"))
                continue
            _, created = Bolim.objects.get_or_create(xojalik=xojalik, name=row["name"].strip())
            self._count(created, counter)
        return tuple(counter)

    def seed_types(self, model, rows, with_month=False):
        """Avval asosiy (parent'siz) turlar, keyin bolalari. Takror nom — birinchisi qoladi."""
        counter = [0, 0]
        seen = set()
        ordered = sorted(rows, key=lambda r: bool(r.get("parent_name")))
        for row in ordered:
            name = row["name"].strip()
            parent_name = _blank_to_none(row.get("parent_name"))
            key = (name, parent_name)
            if key in seen:
                continue
            seen.add(key)
            parent = model.objects.filter(name=parent_name).first() if parent_name else None
            defaults = {"description": _blank_to_none(row.get("description"))}
            if with_month:
                defaults["month"] = row.get("month")
            obj = model.objects.filter(name=name, parent=parent).first()
            if obj is None:
                model.objects.create(name=name, parent=parent, **defaults)
                counter[0] += 1
            else:
                for field, value in defaults.items():
                    setattr(obj, field, value)
                obj.save()
                counter[1] += 1
        return tuple(counter)
