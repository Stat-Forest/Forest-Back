"""
MIB Push Service: tekshirish va shartnomalarni qo'lda (qayta) yuborish.

    python manage.py mib_push --check                          # kalit o'qiladimi, token yaratiladimi
    python manage.py mib_push --since 2026-08-20               # DRY-RUN: nechta shartnoma yuboriladi
    python manage.py mib_push --since 2026-08-20 --send        # yuborish (o'zgarmaganlari o'tkaziladi)
    python manage.py mib_push --number SH-12 --send --force    # aniq shartnoma(lar)ni majburan
    python manage.py mib_push --all --send                     # hammasi
    python manage.py mib_push --retry-failed                   # xato bilan tugaganlarni qayta

--since: `updated_at` shu sanadan keyin bo'lgan shartnomalar (eski billing'dan
ko'chirilganlarda `updated_at` eski billing'dagi qiymat).
Yuborish sinxron (Celery'siz). `MIB_PUSH_ENABLED` dan qat'i nazar ishlaydi.
"""
from datetime import datetime, time

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.billing.models import Contract, MibPushLog
from apps.billing.services import mib_push


class Command(BaseCommand):
    help = "MIB Push Service: tekshirish va shartnomalarni yuborish"

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true", help="Sozlama va kalitni tekshirish")
        parser.add_argument("--since", help="YYYY-MM-DD: shu sanadan beri o'zgargan shartnomalar")
        parser.add_argument("--number", action="append", default=[], help="Shartnoma raqami yoki tizim raqami (takrorlanadi)")
        parser.add_argument("--all", action="store_true", help="Barcha shartnomalar")
        parser.add_argument("--send", action="store_true", help="Haqiqatan yuborish (aks holda DRY-RUN)")
        parser.add_argument("--force", action="store_true", help="O'zgarmagan bo'lsa ham yuborish")
        parser.add_argument("--retry-failed", action="store_true", help="Xato bilan tugaganlarni qayta yuborish")

    def handle(self, *args, **opts):
        if opts["check"]:
            return self._check()
        if opts["retry_failed"]:
            sent = mib_push.retry_failed()
            self.stdout.write(f"Qayta yuborildi: {sent}; hali xato: {MibPushLog.objects.filter(status=MibPushLog.Status.FAILED).count()}")
            return

        qs = self._select(opts)
        total = qs.count()
        self.stdout.write(f"Tanlangan shartnomalar: {total}")
        if not opts["send"]:
            self.stdout.write("DRY-RUN — yuborish uchun --send qo'shing")
            return

        stats = {"sent": 0, "failed": 0, "skipped": 0}
        for index, contract_id in enumerate(qs.values_list("id", flat=True).iterator(), start=1):
            log = mib_push.push_contract(contract_id, force=opts["force"])
            if log is None:
                stats["skipped"] += 1
            elif log.status == MibPushLog.Status.SENT:
                stats["sent"] += 1
            else:
                stats["failed"] += 1
                if stats["failed"] == 1:
                    self.stderr.write(f"Birinchi xato ({log.contract_number}): {log.error}")
            if index % 100 == 0 or index == total:
                self.stdout.write(f"{index}/{total}: {stats}")
        self.stdout.write(self.style.SUCCESS(f"Tugadi: {stats}"))

    def _select(self, opts):
        if not (opts["since"] or opts["number"] or opts["all"]):
            raise CommandError("--since, --number yoki --all dan birini bering (yoki --check / --retry-failed)")
        qs = Contract.objects.all()
        if opts["since"]:
            try:
                day = datetime.strptime(opts["since"], "%Y-%m-%d").date()
            except ValueError as exc:
                raise CommandError("--since formati: YYYY-MM-DD") from exc
            qs = qs.filter(updated_at__gte=timezone.make_aware(datetime.combine(day, time.min)))
        if opts["number"]:
            numbers = [n.strip() for n in opts["number"] if n.strip()]
            qs = qs.filter(contract_number__in=numbers) | qs.filter(number__in=numbers)
        return qs.order_by("updated_at")

    def _check(self):
        cfg = mib_push.config()
        self.stdout.write(f"ENABLED={cfg['ENABLED']} BASE_URL={cfg['BASE_URL']} SYSTEM_NAME={cfg['SYSTEM_NAME']} SUBSCRIBERS={cfg['SUBSCRIBERS']}")
        self.stdout.write(f"PRIVATE_KEY_PATH={cfg['PRIVATE_KEY_PATH']}")
        try:
            mib_push.make_token()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"Token yaratilmadi: {type(exc).__name__}: {exc}") from exc
        self.stdout.write(self.style.SUCCESS("Kalit o'qildi, JWT (RS512) yaratildi"))
        if not cfg["ENABLED"]:
            self.stdout.write(self.style.WARNING("MIB_PUSH_ENABLED=False — avtomatik yuborish o'chiq"))
