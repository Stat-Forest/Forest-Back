"""
Mahalla -> o'rmon xo'jaligi biriktirishlarini Excel'dan yuklash (javob A2).

Ustunlar: маҳалла коди | хўжалик (Organization UUID yoki aniq nomi) | амал бошланиши | амал тугаши.
Bir xil (mahalla, xo'jalik, boshlanish) qator qayta yuklansa — o'zgarishsiz.
Davr kesishsa model validatsiyasi rad etadi (qator raqami bilan hisobot).
"""
import uuid

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.general.models import Organization
from apps.yashil.models import Mahalla, SupplierAssignment

from ._xlsx import ImportReport, parse_date, read_sheet, text
from .yashil_import_mahallas import _message

HEADERS = {
    "mahalla": ["маҳалла коди", "mahalla kodi", "маҳалла", "mahalla"],
    "organization": ["хўжалик", "xo'jalik", "xojalik", "ташкилот", "tashkilot"],
    "valid_from": ["амал бошланиши", "amal boshlanishi"],
}


class Command(BaseCommand):
    help = "Yashil mahalla: mahalla -> o'rmon xo'jaligi biriktirishlarini Excel'dan yuklaydi."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--source", default="", help="Asos hujjat (source_doc)")

    def handle(self, *args, **options):
        sheet = read_sheet(options["file"], HEADERS)
        report = ImportReport(self.stdout, options["dry_run"])
        with transaction.atomic():
            for row_no, row in sheet.rows:
                try:
                    code = text(sheet.col(row, *HEADERS["mahalla"], required=True))
                    mahalla = Mahalla.objects.filter(source_code=code).first()
                    if mahalla is None:
                        raise ValueError(f"mahalla kodi topilmadi: {code}")
                    org = _find_org(text(sheet.col(row, *HEADERS["organization"], required=True)))
                    valid_from = parse_date(sheet.col(row, *HEADERS["valid_from"], required=True))
                    valid_to = parse_date(sheet.col(row, "амал тугаши", "amal tugashi"))
                    existing = SupplierAssignment.objects.filter(mahalla=mahalla, organization=org, valid_from=valid_from).first()
                    if existing is not None:
                        if existing.valid_to != valid_to:
                            existing.valid_to = valid_to
                            existing.full_clean()
                            if not report.dry_run:
                                existing.save()
                            report.updated += 1
                        else:
                            report.unchanged += 1
                        continue
                    obj = SupplierAssignment(mahalla=mahalla, organization=org, valid_from=valid_from,
                                             valid_to=valid_to, source_doc=options["source"])
                    obj.full_clean()
                    if not report.dry_run:
                        obj.save()
                    report.created += 1
                except (ValueError, ValidationError) as exc:
                    report.error(row_no, _message(exc))
            if report.dry_run:
                transaction.set_rollback(True)
        report.print()


def _find_org(value: str) -> Organization:
    try:
        return Organization.objects.get(pk=uuid.UUID(value))
    except (ValueError, Organization.DoesNotExist):
        pass
    org = Organization.objects.filter(name__iexact=value).first()
    if org is None:
        raise ValueError(f"tashkilot topilmadi: {value}")
    return org
