"""
O'lchov birliklari va miqdor aniqligi (TZ §4, javob В4).

tup / dona / komplekt / daraxt — butun son; kg / metr — 3 o'nlik xona;
ga — 4 o'nlik xona. Miqdor har doim musbat.
"""
from decimal import Decimal

UNIT_PRECISION = {
    "tup": 0,
    "dona": 0,
    "komplekt": 0,
    "daraxt": 0,
    "kg": 3,
    "metr": 3,
    "ga": 4,
}

UNIT_LABELS = {
    "tup": ("туп", "tup"),
    "dona": ("дона", "dona"),
    "komplekt": ("комплект", "komplekt"),
    "daraxt": ("дарахт", "daraxt"),
    "kg": ("кг", "kg"),
    "metr": ("метр", "metr"),
    "ga": ("га", "ga"),
}

UNIT_CHOICES = [(code, labels[0]) for code, labels in UNIT_LABELS.items()]


def precision_for(unit: str) -> int:
    return UNIT_PRECISION[unit]


def quantity_error(value: Decimal, unit: str) -> str | None:
    """Noto'g'ri miqdor uchun xato matni (kirill), to'g'ri bo'lsa None."""
    if unit not in UNIT_PRECISION:
        return "Номаълум ўлчов бирлиги"
    value = Decimal(value)
    if value <= 0:
        return "Миқдор мусбат бўлиши керак"
    exponent = -value.normalize().as_tuple().exponent
    if exponent > UNIT_PRECISION[unit]:
        if UNIT_PRECISION[unit] == 0:
            return "Бу бирлик учун миқдор бутун сон бўлиши керак"
        return f"Бу бирлик учун кўпи билан {UNIT_PRECISION[unit]} ўнлик хона рухсат этилади"
    return None
