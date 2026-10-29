"""
Yaxlitlik tekshiruvi (TZ §17.3, Q36): hujjat hash'lari va imzolar, fayllar, ledger, sanoqlar.

    python manage.py yashil_integrity_check --json > snapshot.json      # bekapdan keyin
    python manage.py yashil_integrity_check --compare snapshot.json     # tiklangan muhitda
"""
import json

from django.core.management.base import BaseCommand, CommandError

from apps.yashil.services import integrity


class Command(BaseCommand):
    help = "Yashil mahalla: ma'lumotlar yaxlitligi va tiklashdan keyingi moslik"

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--no-files", action="store_true", help="Fayllar mavjudligini tekshirmaslik")
        parser.add_argument("--compare", default="", help="Avvalgi --json natijasi bilan solishtirish")
        parser.add_argument("--strict", action="store_true", help="Muammo bo'lsa xato kodi")

    def handle(self, *args, **opts):
        report = integrity.collect(check_files=not opts["no_files"])
        if opts["json"]:
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        else:
            self.stdout.write("Саноқлар: " + ", ".join(f"{k}={v}" for k, v in report["counts"].items()))
            self.stdout.write(f"Бузилган ҳужжат версиялари: {report['tampered_count']}")
            for name, info in report["missing_files"].items():
                if info["missing"]:
                    self.stdout.write(f"Йўқ файллар {name}: {info['missing']}")
            self.stdout.write(f"Ledger хатолари: {report['ledger_error_count']}; манфий ўрмон позициялари: {report['negative_forest_items']}")
            self.stdout.write("Яхлитлик: OK" if report["ok"] else "Яхлитлик: МУАММО БОР")
        problems = []
        if opts["compare"]:
            with open(opts["compare"], encoding="utf-8") as fh:
                expected = json.load(fh)
            diff = integrity.compare(expected, report)
            if not opts["json"]:
                self.stdout.write("Мос: захира ва тикланган маълумот бир хил" if not diff else "Фарқлар:\n  " + "\n  ".join(diff))
            problems += diff
        if opts["strict"] and not report["ok"]:
            problems.append("integrity")
        if problems:
            raise CommandError(f"Moslik/yaxlitlik muammosi: {len(problems)}")
