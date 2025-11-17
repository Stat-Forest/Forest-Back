import re
from decimal import Decimal, InvalidOperation
from typing import Any


def is_number(value: Any) -> bool:
    """
    Universal number tekshiruvchi.
    Quyidagi holatlarni `True` deb qaytaradi:
        - Int, float, Decimal
        - String ichida raqamlar: '12', '12.5', '0.001'
    Aks holda `False`.
    """
    if value is None:
        return False

    # Raqam bo‘lsa (int, float, Decimal) - valid
    if isinstance(value, (int, float, Decimal)):
        return True

    # String bo‘lsa, raqam formatini tekshiramiz
    try:
        value = str(value).strip()
        if not value:
            return False
        # Regex: butun yoki kasr sonlar uchun
        return re.match(r'^-?\d+(\.\d+)?$', value) is not None
    except Exception:
        return False


def safe_decimal(value) -> Decimal:
    """
    Agar value son bo‘lsa, Decimal qaytaradi.
    Aks holda Decimal(0) qaytaradi.
    """
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(0)