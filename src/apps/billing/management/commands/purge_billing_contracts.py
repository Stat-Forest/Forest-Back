"""
Ijara billing shartnomalarini to'liq o'chirish (bazani tozalash).

    python manage.py purge_billing_contracts                       # DRY-RUN: faqat hisobot
    python manage.py purge_billing_contracts --confirm-count 5155  # hammasini o'chirish
    python manage.py purge_billing_contracts --only-imported --confirm-count 5154

O'chiriladi: shartnomalar va ularga bog'liq hamma narsa (yillik summalar, yer/faoliyat/
imtiyoz turlari, harakatlar va mahsulotlar, fayllar — bazadan VA diskdan, tarix) hamda
boshqa shartnomasi qolmagan ijarachilar.
Tegilmaydi: ma'lumotnomalar (viloyat, tuman, xo'jalik, bo'lim, turlar), GIS
konturlar, billing foydalanuvchilari va ularning xo'jalik biriktirishlari.

--only-imported: faqat eski billing'dan `import_billing_contracts` bilan ko'chirilganlar
(tarixida `legacy_reason` bor yoki fayli documents/billing/contracts/legacy/ ostida).

--confirm-count: tanlangan shartnomalar soni bilan aynan mos kelishi shart — aks holda
hech narsa o'chirilmaydi (tasodifiy ishga tushirishdan himoya). Diskdagi fayllar faqat
bazadagi o'chirish muvaffaqiyatli commit bo'lgandan keyin o'chiriladi.
"""
import os

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.billing.management.commands.import_billing_contracts import LEGACY_PREFIX
from apps.billing.models import (
    Contract, ContractAction, ContractActionProduct, ContractActivity, ContractFile, ContractHistory,
    ContractLand, ContractPrivilege, ContractYearlyAmount, Renter,
)

CACHE_PATTERNS = ("billing:public:*", "dashboard:*", "*rent_stats*")


class Command(BaseCommand):
    help = "Billing shartnomalarini (bog'liq ma'lumotlar va fayllar bilan) o'chiradi. Standart: DRY-RUN."

    def add_arguments(self, parser):
        parser.add_argument("--only-imported", action="store_true",
                            help="Faqat eski billing'dan import qilingan shartnomalar")
        parser.add_argument("--confirm-count", type=int, default=None,
                            help="O'chirish uchun: tanlangan shartnomalar soni (aynan mos kelishi shart)")

    def _selected(self, only_imported):
        qs = Contract.objects.all()
        if only_imported:
            legacy = Q(history__data__has_key="legacy_reason") | Q(files__file__startswith=f"{LEGACY_PREFIX}/")
            qs = qs.filter(id__in=Contract.objects.filter(legacy).values("id"))
        return qs

    def handle(self, *args, only_imported=False, confirm_count=None, **options):
        contracts = self._selected(only_imported)
        ids = list(contracts.values_list("id", flat=True))
        renter_ids = set(contracts.values_list("renter_id", flat=True))
        files = ContractFile.objects.filter(contract_id__in=ids)
        file_names = [n for n in files.values_list("file", flat=True) if n]
        orphan_renters = (
            Renter.objects.filter(id__in=renter_ids)
            .exclude(contracts__in=Contract.objects.exclude(id__in=ids))
        )

        actions = ContractAction.objects.filter(contract_id__in=ids)
        counts = [
            ("Shartnomalar", len(ids)),
            ("Yillik summalar", ContractYearlyAmount.objects.filter(contract_id__in=ids).count()),
            ("Yer turlari", ContractLand.objects.filter(contract_id__in=ids).count()),
            ("Faoliyat turlari", ContractActivity.objects.filter(contract_id__in=ids).count()),
            ("Imtiyozlar", ContractPrivilege.objects.filter(contract_id__in=ids).count()),
            ("Harakatlar", actions.count()),
            ("Harakat mahsulotlari", ContractActionProduct.objects.filter(action__in=actions).count()),
            ("Fayllar (baza)", len(file_names)),
            ("Tarix yozuvlari", ContractHistory.objects.filter(contract_id__in=ids).count()),
            ("Ijarachilar (boshqa shartnomasi yo'q)", orphan_renters.count()),
        ]
        existing = [n for n in file_names if default_storage.exists(n)]
        size_mb = sum(default_storage.size(n) for n in existing) / (1024 * 1024)

        mode = "faqat import qilinganlar" if only_imported else "BARCHA shartnomalar"
        dry = confirm_count is None
        self.stdout.write(f"{'DRY-RUN' if dry else 'O`CHIRISH'} — {mode}")
        for label, n in counts:
            self.stdout.write(f"  {label}: {n}")
        self.stdout.write(f"  Diskdagi fayllar: {len(existing)} ({size_mb:.1f} MB)")
        self.stdout.write(f"  Qoladigan shartnomalar: {Contract.objects.exclude(id__in=ids).count()}")

        if dry:
            self.stdout.write(self.style.WARNING(
                f"Hech narsa o'chirilmadi. O'chirish uchun: --confirm-count {len(ids)}"
                + (" --only-imported" if only_imported else "")))
            return
        if confirm_count != len(ids):
            raise CommandError(
                f"--confirm-count {confirm_count} tanlangan shartnomalar soniga ({len(ids)}) mos emas. "
                "Hech narsa o'chirilmadi.")

        orphan_ids = list(orphan_renters.values_list("id", flat=True))
        with transaction.atomic():
            Contract.objects.filter(id__in=ids).delete()  # CASCADE: yillik, turlar, harakatlar, fayllar, tarix
            deleted_renters, _ = Renter.objects.filter(id__in=orphan_ids, contracts__isnull=True).delete()
            transaction.on_commit(lambda: self._delete_files(existing))
            transaction.on_commit(self._clear_caches)

        self.stdout.write(self.style.SUCCESS(
            f"O'chirildi: {len(ids)} shartnoma, {deleted_renters} ijarachi, {len(existing)} fayl diskdan. "
            f"Qolgan shartnomalar: {Contract.objects.count()}"))

    def _delete_files(self, names):
        dirs = set()
        for name in names:
            try:
                default_storage.delete(name)
                dirs.add(os.path.dirname(os.path.join(settings.MEDIA_ROOT, name)))
            except OSError as e:
                self.stderr.write(f"Fayl o'chirilmadi: {name}: {e}")
        # Bo'shab qolgan legacy papkalarni tozalash (MEDIA_ROOT'dan yuqoriga chiqmaydi)
        root = os.path.realpath(settings.MEDIA_ROOT)
        for d in sorted(dirs, key=len, reverse=True):
            d = os.path.realpath(d)
            while d.startswith(root + os.sep) and d != root:
                try:
                    os.rmdir(d)
                except OSError:
                    break
                d = os.path.dirname(d)

    def _clear_caches(self):
        for pattern in CACHE_PATTERNS:
            try:
                cache.delete_pattern(pattern)
            except Exception:  # LocMem va h.k. — delete_pattern yo'q
                pass
