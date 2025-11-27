from decimal import Decimal, ROUND_HALF_UP


def round_decimal(val: Decimal, places=2) -> Decimal:
    return val.quantize(Decimal(f"1.{'0'*places}"), rounding=ROUND_HALF_UP)
