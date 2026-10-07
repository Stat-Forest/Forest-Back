"""Shartnoma tarixi (ContractHistory) uchun yordamchilar: snapshot, diff, yozish."""
from decimal import Decimal

from apps.billing.models import Contract, ContractHistory

SNAPSHOT_FIELDS = (
    "contract_number", "status", "contract_date", "expired_date", "auction_date", "exemptioned_date",
    "canceled_date", "cancel_reason", "rent_amount", "paid_amount", "penalty_amount", "rent_area",
    "cadastral_number", "circle", "section", "counter", "massive", "latitude", "longitude",
)
RELATED_FIELDS = ("renter", "xojalik", "bolim", "region", "district")


def _plain(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def snapshot(contract: Contract) -> dict:
    """Tarix uchun shartnomaning JSON'ga mos holati."""
    data = {field: _plain(getattr(contract, field)) for field in SNAPSHOT_FIELDS}
    for field in RELATED_FIELDS:
        related = getattr(contract, field, None)
        data[field] = {"id": str(related.id), "name": str(related)} if related else None
    data["has_boundary"] = bool(contract.boundary_geojson)
    return data


def diff(old: dict, new: dict) -> dict:
    """Faqat o'zgargan kalitlar: {"field": {"old": ..., "new": ...}}."""
    return {key: {"old": old.get(key), "new": new.get(key)} for key in new if old.get(key) != new.get(key)}


def record(contract: Contract, user, reason: str, data: dict | None = None) -> ContractHistory:
    return ContractHistory.objects.create(
        contract=contract,
        executor=user if getattr(user, "is_authenticated", False) else None,
        reason=reason,
        data=data or {},
    )
