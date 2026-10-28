"""Buyurtma raqami `YM-YYYY-NNNNNN` (javob Ж5): yil bo'yicha, atomar, qayta ishlatilmaydi."""
from datetime import date

from django.db import transaction

from apps.yashil.models import OrderSequence

PREFIX = "YM"


def next_order_number(on: date | None = None) -> str:
    on = on or date.today()
    with transaction.atomic():
        seq, _ = OrderSequence.objects.select_for_update().get_or_create(year=on.year)
        seq.last += 1
        seq.save(update_fields=["last"])
        return f"{PREFIX}-{on.year}-{seq.last:06d}"


def act_number(order_number: str, index: int) -> str:
    return f"{order_number}/A{index}"
