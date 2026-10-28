"""
Mahallalar ro'yxatini Excel'dan yuklash (javob A1).

Ustunlar (kirill yoki lotin): манба коди | вилоят коди | туман коди | маҳалла номи |
манзил | фаол | амал бошланиши [| амал тугаши]. Viloyat/tuman kodlari — billing
ma'lumotnomasidagi (MHOBT) kodlar. `source_code` bo'yicha idempotent (update_or_create).
"""
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.billing.models import District, Region
from apps.yashil.models import Mahalla

from ._xlsx import ImportReport, parse_bool, parse_date, read_sheet, text

HEADERS = {
    "source_code": ["манба коди", "manba kodi", "код", "kod"],
    "region_code": ["вилоят коди", "viloyat kodi"],
    "district_code": ["туман коди", "tuman kodi"],
    "name": ["маҳалла номи", "mahalla nomi", "номи", "nomi"],
}


class Command(BaseCommand):
    help = "Yashil mahalla: mahallalar ro'yxatini Excel'dan yuklaydi (source_code bo'yicha idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        sheet = read_sheet(options["file"], HEADERS)
        report = ImportReport(self.stdout, options["dry_run"])
        regions = {r.code: r for r in Region.objects.all()}
        districts = {d.code: d for d in District.objects.select_related("region")}

        with transaction.atomic():
            for row_no, row in sheet.rows:
                try:
                    source_code = text(sheet.col(row, *HEADERS["source_code"], required=True))
                    region_code = text(sheet.col(row, *HEADERS["region_code"], required=True))
                    district_code = text(sheet.col(row, *HEADERS["district_code"], required=True))
                    name = text(sheet.col(row, *HEADERS["name"], required=True))
                    region = regions.get(region_code)
                    district = districts.get(district_code)
                    if region is None:
                        raise ValueError(f"viloyat kodi topilmadi: {region_code}")
                    if district is None or district.region_id != region.id:
                        raise ValueError(f"tuman kodi topilmadi yoki viloyatga mos emas: {district_code}")
                    values = {
                        "name": name,
                        "region": region,
                        "district": district,
                        "address": text(sheet.col(row, "манзил", "manzil")),
                        "is_active": parse_bool(sheet.col(row, "фаол", "faol"), default=True),
                    }
                    valid_from = parse_date(sheet.col(row, "амал бошланиши", "amal boshlanishi"))
                    valid_to = parse_date(sheet.col(row, "амал тугаши", "amal tugashi"))
                    if valid_from:
                        values["valid_from"] = valid_from
                    values["valid_to"] = valid_to
                    existing = Mahalla.objects.filter(source_code=source_code).first()
                    if existing is None:
                        Mahalla(source_code=source_code, **values).full_clean()
                        if not report.dry_run:
                            Mahalla.objects.create(source_code=source_code, **values)
                        report.created += 1
                    else:
                        changed = any(getattr(existing, k) != v for k, v in values.items())
                        if changed:
                            for k, v in values.items():
                                setattr(existing, k, v)
                            existing.full_clean()
                            if not report.dry_run:
                                existing.save()
                            report.updated += 1
                        else:
                            report.unchanged += 1
                except (ValueError, ValidationError) as exc:
                    report.error(row_no, _message(exc))
            if report.dry_run:
                transaction.set_rollback(True)
        report.print()


def _message(exc) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(f"{k}: {', '.join(v)}" for k, v in exc.message_dict.items()) if hasattr(exc, "message_dict") else "; ".join(exc.messages)
    return str(exc)
