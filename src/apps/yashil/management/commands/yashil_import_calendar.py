"""
Ishlab chiqarish kalendari: bayram/dam olish va ko'chirilgan ish kunlari (javob Д1).

Ustunlar: сана | тури (байрам / дам олиш / holiday  yoki  иш куни / ish kuni / workday) | изоҳ.
Sana bo'yicha idempotent. `--source` — rasmiy hujjat rekviziti.
"""
from django.core.management.base import BaseCommand

from apps.yashil.services.imports import import_calendar

from ._xlsx import run_import


class Command(BaseCommand):
    help = "Yashil mahalla: ishlab chiqarish kalendarini Excel'dan yuklaydi (sana bo'yicha idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True)
        parser.add_argument("--source", default="", help="Manba hujjat rekviziti")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        run_import(self, import_calendar, options["file"], dry_run=options["dry_run"], partial=True, source_ref=options["source"])
