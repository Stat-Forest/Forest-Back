"""
Modul API'sining OpenAPI fayli (TZ §19.1, §21).

    python manage.py yashil_openapi --out docs/yashil/openapi-yashil.yaml
    python manage.py yashil_openapi --out docs/yashil/openapi-yashil.yaml --check   # fayl eskirganmi
    python manage.py yashil_openapi --json                                          # stdout'ga JSON
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from drf_spectacular.renderers import OpenApiYamlRenderer

from apps.yashil.openapi import build_schema


class Command(BaseCommand):
    help = "Yashil mahalla: OpenAPI tavsifini yaratish"

    def add_arguments(self, parser):
        parser.add_argument("--out", default="", help="YAML fayl yo'li (bo'lmasa stdout)")
        parser.add_argument("--json", action="store_true", help="YAML o'rniga JSON")
        parser.add_argument("--check", action="store_true", help="--out fayli joriy kod bilan mos bo'lmasa xato")

    def handle(self, *args, **opts):
        schema, problems = build_schema(collect_problems=True)
        for p in problems:
            self.stderr.write(p)
        if opts["json"]:
            text = json.dumps(schema, ensure_ascii=False, indent=2) + "\n"
        else:
            text = OpenApiYamlRenderer().render(schema, renderer_context={}).decode("utf-8")
        if not opts["out"]:
            self.stdout.write(text)
            return
        out = Path(opts["out"])
        if opts["check"]:
            if not out.exists() or out.read_text(encoding="utf-8") != text:
                raise CommandError(f"{out} eskirgan — qayta yarating: python manage.py yashil_openapi --out {out}")
            self.stdout.write(f"{out}: mos")
            return
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        paths = len(schema["paths"])
        ops = sum(1 for item in schema["paths"].values() for m in item if m in ("get", "post", "put", "patch", "delete"))
        self.stdout.write(f"{out}: {paths} manzil, {ops} amal" + (f", {len(problems)} ogohlantirish" if problems else ""))
