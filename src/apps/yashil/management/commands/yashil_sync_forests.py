"""
Statdagi viloyat o'rmon xo'jaliklarini yetkazib beruvchi qilish (idempotent).

    python manage.py yashil_sync_forests --dry-run   # kimlar qo'shilishini ko'rish
    python manage.py yashil_sync_forests
"""
from django.core.management.base import BaseCommand

from apps.yashil.services import supplier_sync


class Command(BaseCommand):
    help = "Yashil mahalla: nomida «o'rmon» bo'lgan viloyat tashkilotlariga o'rmon xo'jaligi profili ochish"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Faqat ro'yxat, hech narsa yozilmaydi")

    def handle(self, *args, **opts):
        candidates = list(supplier_sync.forest_candidates())
        for org in candidates:
            self.stdout.write(f"  {org.id} | {org.name} | {org.region} | {org.stir or '—'}")
        if opts["dry_run"]:
            self.stdout.write(f"[DRY-RUN] qo'shiladi: {len(candidates)}")
            return
        created = supplier_sync.sync_forests()
        self.stdout.write(self.style.SUCCESS(f"Qo'shildi: {len(created)} ta o'rmon xo'jaligi"))
