"""
Xatolar: DRF validatsiya xatolarini o'zbekcha matnga o'girish (billing'dagi
uzErrors.py porti) va bo'limlar bo'yicha guruhlangan `BillingValidationError`.
"""
import re

from rest_framework.exceptions import ErrorDetail, ValidationError

CODE_MESSAGES = {
    "required": "To'ldirilishi shart",
    "blank": "Bo'sh bo'lmasligi kerak",
    "null": "Bo'sh bo'lmasligi kerak",
    "invalid": "Noto'g'ri qiymat",
    "max_length": "Juda uzun qiymat",
    "min_length": "Juda qisqa qiymat",
    "max_value": "Ruxsat etilganidan katta qiymat",
    "min_value": "Ruxsat etilganidan kichik qiymat",
    "max_digits": "Raqamlar soni juda ko'p",
    "max_decimal_places": "Verguldan keyin 2 tadan ortiq raqam bo'lmasligi kerak",
    "max_whole_digits": "Butun qismi juda katta",
    "max_string_length": "Juda uzun raqam",
    "does_not_exist": "Tizimda topilmadi",
    "incorrect_type": "Noto'g'ri turdagi qiymat",
    "invalid_choice": "Ruxsat etilmagan qiymat",
    "unique": "Bu qiymat tizimda allaqachon mavjud",
    "date": "Sana noto'g'ri formatda (masalan: 31.01.2026)",
    "datetime": "Sana noto'g'ri formatda (masalan: 31.01.2026)",
}

NUMBER_FIELDS = {
    "rent_amount", "paid_amount", "penalty_amount", "rent_area", "area",
    "export_amount", "own_investment", "vacancy", "contract_amount",
    "calculated_amount", "latitude", "longitude",
}
DATE_FIELDS = {"contract_date", "expired_date", "canceled_date", "auction_date", "exemptioned_date"}

LIMIT_MESSAGES = {
    "max_length": "Ko'pi bilan {n} ta belgi bo'lishi kerak",
    "min_length": "Kamida {n} ta belgi bo'lishi kerak",
    "max_digits": "Ko'pi bilan {n} ta raqam bo'lishi kerak",
    "max_value": "{n} dan katta bo'lmasligi kerak",
    "min_value": "{n} dan kichik bo'lmasligi kerak",
}

_DRF_DEFAULT_RE = re.compile(
    r"^(This field|A valid|Ensure|Invalid pk|Incorrect type|Enter a valid|"
    r"Date has wrong format|Datetime has wrong format|Not a valid|Expected a|"
    r"\".*\" is not a valid choice|.* with this .* already exists|"
    r"Must be a valid|Invalid value|Object with .* does not exist)"
)


def is_drf_default_english(text) -> bool:
    """Loyihaning o'z (o'zbekcha) xabarlari tarjima qilinmaydi."""
    return bool(_DRF_DEFAULT_RE.match(str(text)))


def uz_message(detail, field=None) -> str:
    code = getattr(detail, "code", None)
    if not is_drf_default_english(detail):
        return str(detail)
    if code in LIMIT_MESSAGES:
        numbers = re.findall(r"-?\d+(?:\.\d+)?", str(detail))
        if numbers:
            return LIMIT_MESSAGES[code].format(n=numbers[0])
    if code == "invalid" and field in NUMBER_FIELDS:
        return "Raqam bo'lishi kerak (harf, bo'sh joy yoki belgi bo'lmasin)"
    if code == "invalid" and field in DATE_FIELDS:
        return CODE_MESSAGES["date"]
    if code in CODE_MESSAGES:
        return CODE_MESSAGES[code]
    return str(detail)


def uz_errors(detail, field=None):
    """
    ValidationError.detail (dict/list/ErrorDetail) -> xuddi shu shakldagi
    o'zbekcha tuzilma. Ro'yxatlar bitta matnga birlashtiriladi.
    """
    if isinstance(detail, ValidationError):
        detail = detail.detail
    if isinstance(detail, dict):
        return {str(key): uz_errors(value, str(key)) for key, value in detail.items()}
    if isinstance(detail, (list, tuple)):
        parts = [uz_errors(item, field) for item in detail]
        if all(isinstance(p, str) for p in parts):
            return "; ".join(dict.fromkeys(parts))
        return {f"{i + 1}-yozuv": p for i, p in enumerate(parts) if p}
    if isinstance(detail, ErrorDetail):
        return uz_message(detail, field)
    return str(detail)


def flatten_messages(value) -> str:
    """{field: msg} yoki ichma-ich tuzilmani bitta qatorga yig'adi."""
    if isinstance(value, dict):
        return "; ".join(f"{k}: {flatten_messages(v)}" if k != "non_field_errors" else flatten_messages(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return "; ".join(flatten_messages(v) for v in value)
    return str(value)


class BillingValidationError(Exception):
    """
    Bo'limlar bo'yicha guruhlangan xatolar:
    {"contract": {"field": "xabar"}, "renter": {...}, "lands": {...}, ...}
    """

    def __init__(self, errors: dict):
        super().__init__(flatten_messages(errors))
        self.errors = errors

    @classmethod
    def for_section(cls, section: str, errors) -> "BillingValidationError":
        return cls({section: errors})

    @classmethod
    def field(cls, section: str, field: str, message: str) -> "BillingValidationError":
        return cls({section: {field: message}})
