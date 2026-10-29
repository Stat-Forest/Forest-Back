"""
Pilotdan oldingi tekshiruv (TZ §19.2).

    python manage.py yashil_readiness            # matn
    python manage.py yashil_readiness --json     # JSON
    python manage.py yashil_readiness --strict   # bo'shliq bo'lsa xato bilan tugaydi
"""
import json
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.yashil.services import readiness


class Command(BaseCommand):
    help = "Yashil mahalla: pilot va ishchi muhitga tayyorlik tekshiruvi"

    def add_arguments(self, parser):
        parser.add_argument("--date", default="", help="YYYY-MM-DD (standart: bugun)")
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--strict", action="store_true", help="Bloklovchi bo'shliq bo'lsa xato kodi")
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **opts):
        on = date.fromisoformat(opts["date"]) if opts["date"] else None
        report = readiness.collect(on=on, limit=opts["limit"])
        if opts["json"]:
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            t = report["totals"]
            self.stdout.write(f"Сана: {report['date']} · маҳаллалар {t['mahallas']} · етказиб берувчилар {t['suppliers']} · аъзоликлар {t['memberships']}")
            self.stdout.write("Қоидалар: " + ", ".join(f"{k}={v}" for k, v in report["rules"].items()))
            for s in report["sections"]:
                mark = "OK " if not s["count"] else ("!! " if s["level"] == "blocker" else "?  ")
                self.stdout.write(f"{mark}{s['title']}: {s['count']}")
                for name in s["sample"]:
                    self.stdout.write(f"     - {name}")
            self.stdout.write("Тайёр" if report["ready"] else f"Тайёр эмас: блокловчи {report['blockers']}")
        if opts["strict"] and report["blockers"]:
            raise CommandError(f"Bloklovchi bo'shliqlar: {report['blockers']}")
