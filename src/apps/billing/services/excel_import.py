"""
Excel import: frontend Excel'ni o'qib `rows` (ImportRow ro'yxati) yuboradi;
har qator alohida atomik saqlanadi. Natija:
    {"saved": [0, 2, ...], "errors": {"1": {"contract": {"xojalik_inn": "..."}}}}
"""
import datetime
import logging
import re
from decimal import Decimal, InvalidOperation

from django.db import transaction

from apps.billing.services.contract_writer import save_contract
from apps.billing.services.errors import BillingValidationError

logger = logging.getLogger(__name__)

MAX_ROWS = 200
DATE_FORMATS = ("%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y.%m.%d", "%d.%m.%y", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S")
EXCEL_EPOCH = datetime.date(1899, 12, 30)

CONTRACT_DATE_FIELDS = ("contract_date", "expired_date", "auction_date", "exemptioned_date", "canceled_date")
CONTRACT_NUMBER_FIELDS = ("rent_amount", "paid_amount", "penalty_amount", "rent_area")
CONTRACT_COORD_FIELDS = ("latitude", "longitude")
YEARLY_FIELDS = ("contract_amount", "calculated_amount", "paid_amount", "penalty_amount")
REQUIRED_MESSAGE = "To'ldirilishi shart"
NUMBER_MESSAGE = "Raqam bo'lishi kerak (harf, bo'sh joy yoki belgi bo'lmasin)"
DATE_MESSAGE = "Sana noto'g'ri formatda (masalan: 31.01.2026)"


def parse_date(value):
    """dd.mm.yyyy / yyyy-mm-dd / Excel serial -> ISO sana. Noto'g'ri bo'lsa ValueError."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if 1 < value < 200000:
            return (EXCEL_EPOCH + datetime.timedelta(days=int(value))).isoformat()
        raise ValueError(value)
    text = str(value).strip()
    if re.fullmatch(r"\d+(\.\d+)?", text):
        serial = float(text)
        if 1 < serial < 200000:
            return (EXCEL_EPOCH + datetime.timedelta(days=int(serial))).isoformat()
        raise ValueError(value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(value)


def parse_number(value, places: int = 2):
    """Bo'sh -> 0; '1 234,5' kabi matnlar ham qabul qilinadi. Noto'g'ri bo'lsa ValueError."""
    if value in (None, ""):
        return Decimal(0)
    if isinstance(value, bool):
        raise ValueError(value)
    if isinstance(value, (int, float, Decimal)):
        number = Decimal(str(value))
    else:
        text = str(value).strip().replace(" ", "").replace(" ", "")
        if "," in text and "." not in text:
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")
        try:
            number = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(value) from exc
    return number.quantize(Decimal(1).scaleb(-places))


def normalize_row(row: dict) -> dict:
    """Sana/raqam maydonlarini writer uchun tayyorlaydi; majburiy maydonlarni tekshiradi."""
    row = dict(row or {})
    errors = {}
    contract = dict(row.get("contract") or {})
    contract_errors = {}

    for field in ("contract_date",):
        if contract.get(field) in (None, ""):
            contract_errors[field] = REQUIRED_MESSAGE
    if not str(contract.get("xojalik_inn") or "").strip() and not str(contract.get("xojalik") or "").strip():
        contract_errors["xojalik_inn"] = "Xo'jalik INN yoki nomi to'ldirilishi shart"
    if contract.get("rent_area") in (None, ""):
        contract_errors["rent_area"] = REQUIRED_MESSAGE

    for field in CONTRACT_DATE_FIELDS:
        if field in contract and field not in contract_errors:
            try:
                contract[field] = parse_date(contract[field])
            except ValueError:
                contract_errors[field] = DATE_MESSAGE
    for field in CONTRACT_NUMBER_FIELDS:
        if field in contract and field not in contract_errors:
            try:
                contract[field] = parse_number(contract[field])
            except ValueError:
                contract_errors[field] = NUMBER_MESSAGE
    for field in CONTRACT_COORD_FIELDS:
        if contract.get(field) not in (None, ""):
            try:
                contract[field] = parse_number(contract[field], places=7)
            except ValueError:
                contract_errors[field] = NUMBER_MESSAGE
        elif field in contract:
            contract[field] = None
    if contract.get("xojalik_inn") not in (None, ""):
        contract["xojalik_inn"] = str(contract["xojalik_inn"]).strip().split(".")[0]
    for field in ("region_code", "district_code"):
        if contract.get(field) not in (None, ""):
            contract[field] = str(contract[field]).strip().split(".")[0]
    if contract_errors:
        errors["contract"] = contract_errors
    row["contract"] = contract

    renter = row.get("renter")
    if isinstance(renter, dict):
        renter = dict(renter)
        for field in ("pinfl", "stir", "passport", "phone"):
            if renter.get(field) not in (None, ""):
                renter[field] = str(renter[field]).strip().split(".")[0] if field in ("pinfl", "stir") else str(renter[field]).strip()
        row["renter"] = renter

    for section in ("lands", "activities", "privileges"):
        items = row.get(section)
        if isinstance(items, list):
            section_errors = {}
            cleaned = []
            for index, item in enumerate(items):
                item = dict(item or {})
                label = str(item.get("type") or f"{index + 1}-yozuv")
                if item.get("area") in (None, ""):
                    continue
                try:
                    item["area"] = parse_number(item["area"])
                except ValueError:
                    section_errors[label] = f"Maydon (ga): {NUMBER_MESSAGE}"
                    continue
                cleaned.append(item)
            if section_errors:
                errors[section] = section_errors
            row[section] = cleaned

    yearly = row.get("yearly_amounts")
    if isinstance(yearly, list):
        yearly_errors = {}
        cleaned = []
        for index, item in enumerate(yearly):
            item = dict(item or {})
            year = item.get("year")
            if year in (None, ""):
                continue
            try:
                item["year"] = int(str(year).strip().split(".")[0])
            except ValueError:
                yearly_errors[f"{index + 1}-yozuv"] = f"Yil: {NUMBER_MESSAGE}"
                continue
            for field in YEARLY_FIELDS:
                try:
                    item[field] = parse_number(item.get(field))
                except ValueError:
                    yearly_errors[f"{item['year']}_{field}"] = NUMBER_MESSAGE
            cleaned.append(item)
        if yearly_errors:
            errors["yearly_amounts"] = yearly_errors
        row["yearly_amounts"] = cleaned

    action = row.get("action")
    if isinstance(action, dict):
        action = dict(action)
        action_errors = {}
        for field in ("vacancy", "own_investment"):
            if action.get(field) not in (None, ""):
                try:
                    action[field] = parse_number(action[field])
                except ValueError:
                    action_errors[field] = NUMBER_MESSAGE
        if action_errors:
            errors["action"] = action_errors
        row["action"] = action

    if errors:
        raise BillingValidationError(errors)
    return row


def import_rows(rows: list, user) -> dict:
    saved = []
    errors = {}
    for index, raw in enumerate(rows):
        try:
            with transaction.atomic():
                row = normalize_row(raw)
                save_contract(row, user, from_import=True)
            saved.append(index)
        except BillingValidationError as exc:
            errors[str(index)] = exc.errors
        except Exception as exc:  # noqa: BLE001 — bitta qator xatosi boshqalarini to'xtatmasin
            logger.exception("billing import row %s failed", index)
            errors[str(index)] = {"contract": {"xatolik": str(exc)}}
    return {"saved": saved, "errors": errors}
