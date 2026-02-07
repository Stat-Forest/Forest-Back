from decimal import Decimal
from collections import defaultdict


def to_dec(v):
    if v in ("", None):
        return None
    try:
        return Decimal(str(v).replace(",", "."))
    except:
        return None


def aggregate_target_maps(value_maps):
    """
    ORGANIZATION target_value_map larni yig'adi
    Faqat Reja va Amalda yig'iladi
    % va (+,-) qayta hisoblanadi keyin
    """

    agg = defaultdict(Decimal)

    for vm in value_maps:
        for ordering, value in vm.items():
            dec = to_dec(value)
            if dec is None:
                continue
            agg[ordering] += dec

    # Decimal → string
    result = {}
    for k, v in agg.items():
        if v == v.to_integral_value():
            result[k] = str(v)
        else:
            result[k] = str(v.normalize())

    return result
