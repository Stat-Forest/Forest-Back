"""
Xo'jaliklarning ixcham tashqi chegarasini (`outline_geojson`) boundary_geojson'dan
qurish — landing xaritasi uchun (`/billing/public/xojalik-outlines/`).

    python manage.py build_xojalik_outlines            # hammasi qaytadan
    python manage.py build_xojalik_outlines --missing  # faqat yo'qlari (entrypoint)
"""
from django.core.cache import cache
from django.core.management.base import BaseCommand

from apps.billing.models import XojalikLocation
from apps.billing.services.geo import OUTLINES_CACHE_KEY, build_outline


class Command(BaseCommand):
    help = "XojalikLocation.outline_geojson'ni boundary_geojson'dan quradi"

    def add_arguments(self, parser):
        parser.add_argument("--missing", action="store_true", help="Faqat outline'i yo'q xo'jaliklar")

    def handle(self, *args, missing=False, **options):
        queryset = XojalikLocation.objects.filter(boundary_geojson__isnull=False)
        if missing:
            queryset = queryset.filter(outline_geojson__isnull=True)
        built = 0
        for location in queryset.iterator(chunk_size=10):
            location.outline_geojson = build_outline(location.boundary_geojson)
            location.save(update_fields=["outline_geojson", "updated_at"])
            built += 1
        if built:
            cache.delete(OUTLINES_CACHE_KEY)
        self.stdout.write(f"Xo'jalik chegaralari qurildi: {built}")
