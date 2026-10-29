"""
Mahallalar ro'yxatini Excel'dan yuklash (javob A1).

Ustunlar (kirill yoki lotin): манба коди | вилоят коди | туман коди | маҳалла номи |
манзил | фаол | амал бошланиши [| амал тугаши]. Viloyat/tuman kodlari — billing
ma'lumotnomasidagi (MHOBT) kodlar. `source_code` bo'yicha idempotent.
Xatoli qatorlar tashlab o'tiladi (hisobotda qator raqami bilan).
"""
from django.core.management.base import BaseCommand

from apps.yashil.services.imports import import_mahallas, message_of

from ._xlsx import run_import

_message = message_of  # eski import yo'li


class Command(BaseCommand):
    help = "Yashil mahalla: mahallalar ro'yxatini Excel'dan yuklaydi (source_code bo'yicha idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        run_import(self, import_mahallas, options["file"], dry_run=options["dry_run"], partial=True)
