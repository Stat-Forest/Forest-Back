"""Shartnoma tizim raqami: `{xojalik.code or xojalik.inn or 'X'}-{N}` (xo'jalik bo'yicha ketma-ket)."""
from apps.billing.models import Contract, Xojalik


def generate_contract_number(xojalik: Xojalik) -> str:
    prefix = xojalik.code or xojalik.inn or "X"
    latest = Contract.objects.filter(xojalik=xojalik).order_by("-created_at").values_list("number", flat=True).first()
    number = 0
    if latest:
        try:
            number = int(str(latest).rsplit("-", 1)[-1])
        except ValueError:
            number = 0
    while True:
        number += 1
        candidate = f"{prefix}-{number}"
        if not Contract.objects.filter(number=candidate).exists():
            return candidate
