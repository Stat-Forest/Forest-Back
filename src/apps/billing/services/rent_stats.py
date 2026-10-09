"""
Ijara tushumi statistikasi (billing `GetMonitoringDataView.get_yearly_area_price_stats`
porti — N+1 o'rniga bitta guruhlangan so'rov).

    yearly_area_price_stats(contracts_qs, from_year, to_year) -> dict

Har yil uchun `ContractYearlyAmount` (year filtri) bo'yicha:
  total_area = Σ contract.rent_area, total_calculated = Σ calculated_amount,
  price_per_hectare = total_calculated / total_area.
Javobda faqat yig'indilar — shaxsiy ma'lumot yo'q.
"""
import uuid
from decimal import Decimal

from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.billing.models import ContractYearlyAmount

DEFAULT_FROM_YEAR = 2020
MIN_YEAR, MAX_YEAR = 1990, 2100
ZERO = Value(Decimal("0"), output_field=DecimalField(max_digits=30, decimal_places=2))


class RentStatsParamsError(Exception):
    def __init__(self, errors: dict):
        super().__init__(errors)
        self.errors = errors


def _parse_year(value, field: str, errors: dict):
    if value in (None, ""):
        return None
    try:
        year = int(str(value).strip())
    except (TypeError, ValueError):
        errors[field] = "Yil butun son bo'lishi kerak"
        return None
    if not MIN_YEAR <= year <= MAX_YEAR:
        errors[field] = f"Yil {MIN_YEAR}–{MAX_YEAR} oralig'ida bo'lishi kerak"
        return None
    return year


def parse_rent_stats_params(params):
    """`from_year`, `to_year`, `xojalik` -> (int, int, UUID|None). Default: 2020 .. joriy yil."""
    errors = {}
    from_year = _parse_year(params.get("from_year"), "from_year", errors)
    to_year = _parse_year(params.get("to_year"), "to_year", errors)
    xojalik = (params.get("xojalik") or "").strip() or None
    xojalik_id = None
    if xojalik:
        try:
            xojalik_id = uuid.UUID(xojalik)
        except ValueError:
            errors["xojalik"] = "Noto'g'ri xo'jalik ID"
    if errors:
        raise RentStatsParamsError(errors)
    from_year = from_year or DEFAULT_FROM_YEAR
    to_year = to_year or max(timezone.localdate().year, from_year)
    if from_year > to_year:
        from_year, to_year = to_year, from_year
    return from_year, to_year, xojalik_id


def _num(value: Decimal) -> float:
    return float(round(value, 2))


def yearly_area_price_stats(contracts_qs, from_year: int, to_year: int) -> dict:
    rows = (
        ContractYearlyAmount.objects.filter(
            contract__in=contracts_qs.order_by().values("id"), year__gte=from_year, year__lte=to_year,
        )
        .values("year")
        .annotate(
            total_area=Coalesce(Sum("contract__rent_area"), ZERO),
            total_calculated=Coalesce(Sum("calculated_amount"), ZERO),
        )
        .order_by("year")
    )
    years = []
    for row in rows:
        area, calculated = row["total_area"], row["total_calculated"]
        years.append({
            "year": row["year"],
            "total_area": _num(area),
            "total_calculated": _num(calculated),
            "price_per_hectare": _num(calculated / area) if area else 0.0,
        })

    totals = [y["total_calculated"] for y in years]
    average = round(sum(totals) / len(totals), 2) if totals else 0.0
    if len(years) >= 2:
        first, last = totals[0], totals[-1]
        diff = round(last - first, 2)
        percent = round(diff / first * 100, 2) if first else 0.0
    else:
        diff, percent = 0.0, 0.0
    best = max(years, key=lambda y: y["total_calculated"]) if years else None
    return {
        "from_year": from_year,
        "to_year": to_year,
        "years": years,
        "average_annual": average,
        "growth": {"diff": diff, "percent": percent},
        "max": {"year": best["year"], "total_calculated": best["total_calculated"]} if best else {"year": None, "total_calculated": 0.0},
    }
