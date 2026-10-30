"""
Qabul sinovlari bayonnomasi (TZ §18–19).

    python manage.py yashil_acceptance_protocol --out /tmp/yashil-bayonnoma.docx --environment "test server"
    python manage.py yashil_acceptance_protocol --out blank.docx --no-run     # bo'sh shakl (faqat qo'lda)

Testlar alohida test bazasida ishlaydi (CREATEDB huquqi kerak) — ishchi bazaga tegmaydi,
lekin ishchi serverda emas, test serverda yoki lokal ishga tushiriladi.
"""
import json
import os
import subprocess

from django.core.management.base import BaseCommand, CommandError

from apps.yashil.acceptance import CASES
from apps.yashil.services.protocol import OK, build_protocol_docx, case_summary, default_meta, run_acceptance_tests


def _git_version() -> str:
    if os.environ.get("GIT_COMMIT"):
        return os.environ["GIT_COMMIT"]
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


class Command(BaseCommand):
    help = "Q01–Q36 qabul sinovlari: avtomatik testlarni ishga tushirib DOCX bayonnoma yozadi"

    def add_arguments(self, parser):
        parser.add_argument("--out", required=True, help="DOCX fayl yo'li")
        parser.add_argument("--no-run", action="store_true", help="Testlarsiz bo'sh bayonnoma")
        parser.add_argument("--environment", default="", help="Muhit nomi (masalan: test server)")
        parser.add_argument("--note", default="")
        parser.add_argument("--json", dest="json_out", default="", help="Natijalarni JSON faylga ham yozish")

    def handle(self, *args, **opts):
        if not opts["out"].endswith(".docx"):
            raise CommandError("--out .docx bilan tugashi kerak")
        results = None if opts["no_run"] else run_acceptance_tests(verbosity=1)
        meta = default_meta(opts["environment"], _git_version(), opts["note"])
        build_protocol_docx(results, meta).save(opts["out"])
        if results is not None:
            summaries = [case_summary(c, results) for c in CASES]
            failed = [s["id"] for s in summaries if s["status"] not in (OK, "manual")]
            if opts["json_out"]:
                with open(opts["json_out"], "w", encoding="utf-8") as fh:
                    json.dump({"meta": meta, "cases": summaries, "tests": results}, fh, ensure_ascii=False, indent=2)
            self.stdout.write(f"Bayonnoma: {opts['out']} — avtomatik holatlar: {len(summaries) - 2 - len(failed)}/{len(summaries) - 2} o'tdi")
            if failed:
                raise CommandError("O'tmagan: " + ", ".join(failed))
        else:
            self.stdout.write(f"Bo'sh bayonnoma: {opts['out']}")
