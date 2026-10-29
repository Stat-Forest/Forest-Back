"""Kechikish ustunlarini qayta hisoblash (deploy'dan keyin bir marta; keyin ertalabki vazifa yuritadi)."""
from datetime import date

from django.core.management.base import BaseCommand

from apps.yashil.services.deadlines import recalc_all


class Command(BaseCommand):
    help = "Yashil mahalla: Order.review_due / late_workdays / overdue_stage ustunlarini qayta hisoblaydi."

    def add_arguments(self, parser):
        parser.add_argument("--today", help="YYYY-MM-DD (standart: bugun, Asia/Tashkent)")

    def handle(self, *args, **options):
        today = date.fromisoformat(options["today"]) if options.get("today") else None
        changed = recalc_all(today=today)
        self.stdout.write(f"Yangilandi: {changed} buyurtma")
