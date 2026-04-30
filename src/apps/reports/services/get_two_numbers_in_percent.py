from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


def round_decimal(val: Decimal, places=1) -> Decimal:
    return val.quantize(Decimal(f"1.{'0'*places}"), rounding=ROUND_HALF_UP)


def safe_decimal(value) -> Decimal:
    """
    Qiymatni Decimalga xavfsiz o'giradi.

    Qo'llab-quvvatlaydi:
    - 50.20
    - "50.20"
    - "50,20"
    - None
    - bo'sh string
    """
    if value is None:
        return Decimal("0")

    try:
        normalized = str(value).strip().replace(" ", "").replace(",", ".")
        if not normalized:
            return Decimal("0")
        return Decimal(normalized)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def decimal_to_db_string(value: Decimal) -> str:
    """
    DB uchun standart format.
    DB ichida doim nuqta saqlaymiz.
    """
    return format(safe_decimal(value), "f")


def decimal_to_display_string(value) -> str:
    """
    Faqat ko'rsatish uchun.
    API/Excel/UI'da kerak bo'lsa ishlatiladi.
    """
    return decimal_to_db_string(safe_decimal(value)).replace(".", ",")