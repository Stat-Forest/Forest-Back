"""
Bir nechta shartnomaga ulangan ijarachining nomi shartnomalardan biri orqali
o'zgartirilgan holatlarni chiqaradi (faqat o'qiydi).

Tahrirlash formasi ijarachi id'sini yuborgani uchun umumiy ijarachi joyida
yangilanib ketgan: masalan, B shartnomada ism "Dream taym" ga o'zgartirilsa A
shartnomadagi "Umid kafolat" ham o'zgargan. Shunday shartnomalarni topib, to'g'ri
INN/JSHSHIR bilan qayta kiritish uchun ro'yxat beradi.

    python manage.py billing_renter_conflicts [--name "umid kafolat"]
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.billing.models import Contract, ContractHistory, Renter


class Command(BaseCommand):
    help = "Umumiy ijarachi nomi boshqa shartnoma orqali o'zgartirilgan holatlar (faqat o'qiydi)"

    def add_arguments(self, parser):
        parser.add_argument("--name", default="", help="Ijarachi nomi bo'yicha qidirish (icontains)")

    def handle(self, *args, **options):
        shared_ids = set(
            Renter.objects.annotate(n=Count("contracts")).filter(n__gt=1).values_list("id", flat=True)
        )
        self.stdout.write(f"Bir nechta shartnomaga ulangan ijarachilar: {len(shared_ids)}")

        renames = defaultdict(list)
        history = (
            ContractHistory.objects.filter(reason=ContractHistory.Reason.UPDATED, data__changes__has_key="renter")
            .select_related("contract", "contract__xojalik", "executor")
            .order_by("created_at")
        )
        for row in history.iterator():
            change = row.data["changes"]["renter"]
            old, new = change.get("old") or {}, change.get("new") or {}
            if not old or old.get("id") != new.get("id") or old.get("id") not in {str(i) for i in shared_ids}:
                continue
            if old.get("name") == new.get("name"):
                continue
            renames[old["id"]].append(row)

        name_filter = (options["name"] or "").strip().lower()
        shown = 0
        for renter_id, rows in renames.items():
            renter = Renter.objects.get(id=renter_id)
            names = " ".join(
                [renter.full_name or "", renter.legal_name or ""]
                + [r.data["changes"]["renter"]["old"]["name"] for r in rows]
                + [r.data["changes"]["renter"]["new"]["name"] for r in rows]
            ).lower()
            if name_filter and name_filter not in names:
                continue
            shown += 1
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                f"Ijarachi {renter.id}: hozir «{renter.legal_name or renter.full_name}», "
                f"INN={renter.stir or '-'} JSHSHIR={'bor' if renter.pinfl else '-'}"
            ))
            for contract in Contract.objects.filter(renter=renter).select_related("xojalik").order_by("contract_date"):
                self.stdout.write(
                    f"  shartnoma {contract.id} | {contract.xojalik.name} | raqam {contract.contract_number or '-'} "
                    f"| {contract.contract_date:%d.%m.%Y} | {contract.rent_area} ga"
                )
            for r in rows:
                change = r.data["changes"]["renter"]
                who = r.executor.email if r.executor else "-"
                self.stdout.write(
                    f"  {r.created_at:%d.%m.%Y %H:%M} {who}: shartnoma {r.contract.contract_number or r.contract.number} "
                    f"orqali «{change['old']['name']}» -> «{change['new']['name']}»"
                )
        self.stdout.write("")
        self.stdout.write(f"Nomi boshqa shartnoma orqali o'zgargan umumiy ijarachilar: {shown}")
