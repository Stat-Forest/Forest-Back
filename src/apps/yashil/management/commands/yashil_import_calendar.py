"""
Ishlab chiqarish kalendari: bayram/dam olish va ko'chirilgan ish kunlari (javob Д1).

Ustunlar: сана | тури (байрам / дам олиш / holiday  yoki  иш куни / ish kuni / workday) | изоҳ.
Sana bo'yicha idempotent. `--source` — rasmiy hujjat rekviziti.
"""
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.yashil.models import CalendarDay

from ._xlsx import ImportReport, norm_header, parse_date, read_sheet, text
from .yashil_import_mahallas import _message

HEADERS = {"date": ["сана", "sana", "date"], "kind": ["тури", "turi", "kind"]}
WORKDAY_WORDS = {norm_header(w) for w in ("иш куни", "ish kuni", "workday", "ишкуни", "кўчирилган иш куни")}
HOLIDAY_WORDS = {norm_header(w) for w in ("байрам", "bayram", "дам олиш", "dam olish", "holiday", "дам олиш куни")}


class Command(BaseCommand):
    help = "Yashil mahalla: ishlab chiqarish kalendarini Excel'dan yuklaydi (sana bo'yicha idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True)
        parser.add_argument("--source", default="", help="Manba hujjat rekviziti")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        sheet = read_sheet(options["file"], HEADERS)
        report = ImportReport(self.stdout, options["dry_run"])
        with transaction.atomic():
            for row_no, row in sheet.rows:
                try:
                    day = parse_date(sheet.col(row, *HEADERS["date"], required=True))
                    kind_raw = norm_header(text(sheet.col(row, *HEADERS["kind"], required=True)))
                    if kind_raw in WORKDAY_WORDS:
                        kind = CalendarDay.Kind.WORKDAY
                    elif kind_raw in HOLIDAY_WORDS:
                        kind = CalendarDay.Kind.HOLIDAY
                    else:
                        raise ValueError(f"turi tushunarsiz: {kind_raw!r} (байрам / иш куни)")
                    values = {"kind": kind, "note": text(sheet.col(row, "изоҳ", "izoh", "note")), "source_ref": options["source"]}
                    existing = CalendarDay.objects.filter(date=day).first()
                    if existing is None:
                        if not report.dry_run:
                            CalendarDay.objects.create(date=day, **values)
                        report.created += 1
                    elif any(getattr(existing, k) != v for k, v in values.items()):
                        for k, v in values.items():
                            setattr(existing, k, v)
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
