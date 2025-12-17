from decimal import Decimal


def normalize_decimal_input_dote(value):
    """
    2,5  -> 2.5
    10,1 -> 10.1
    """
    if value is None:
        return value

    if isinstance(value, (int, float, Decimal)):
        return str(value)

    if isinstance(value, str):
        value = value.strip()

        # faqat raqam bo‘lsa ishlaymiz
        if "," in value and "." not in value:
            value = value.replace(",", ".")

        return value

    return value
