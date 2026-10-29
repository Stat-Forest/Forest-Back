"""
Mahalla -> o'rmon xo'jaligi biriktirishlarini Excel'dan yuklash (javob A2).

Ustunlar: маҳалла коди | хўжалик (Organization UUID yoki aniq nomi) | амал бошланиши | амал тугаши.
Bir xil (mahalla, xo'jalik, boshlanish) qator qayta yuklansa — o'zgarishsiz.
Davr kesishsa model validatsiyasi rad etadi (qator raqami bilan hisobot).
"""
from django.core.management.base import BaseCommand

from apps.yashil.services.imports import import_assignments

from ._xlsx import run_import


class Command(BaseCommand):
    help = "Yashil mahalla: mahalla -> o'rmon xo'jaligi biriktirishlarini Excel'dan yuklaydi."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--source", default="", help="Asos hujjat (source_doc)")

    def handle(self, *args, **options):
        run_import(self, import_assignments, options["file"], dry_run=options["dry_run"], partial=True, source_doc=options["source"])
