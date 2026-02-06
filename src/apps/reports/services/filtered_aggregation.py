from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Tuple

from django.db.models import Prefetch

from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn, Plant
from apps.utils.translation import get_translated_field
from apps.utils.services import RegionChoices


@dataclass
class PeriodRange:
    kind: str  # "year" | "quarter"
    year: int
    quarter: int | None = None


def parse_period(period: str) -> PeriodRange:
    """
    Accepts formats:
      - YYYY (year)
      - YYYY-Qn (quarter: Q1..Q4)
    Returns PeriodRange.
    """
    p = (period or "").strip()
    if not p:
        raise ValueError("period is required")
    if "-Q" in p:
        year_s, q_s = p.split("-Q", 1)
        year = int(year_s)
        q = int(q_s)
        if q not in (1, 2, 3, 4):
            raise ValueError("quarter must be 1..4")
        return PeriodRange(kind="quarter", year=year, quarter=q)
    # yearly
    year = int(p)
    return PeriodRange(kind="year", year=year)


def filter_reports_by_period(statement, deadline_id):
    """
    Deadline FK asosida qat’iy filter.
    Hech qanday string parsing YO‘Q.
    """

    qs = Report.objects.filter(
        statement=statement,
        deadline_id=deadline_id,
        is_report=True,
        status=Report.StatusChoices.ACCEPTED,
        is_general=False,
        is_individual_general=False,
        is_republic=False,
    )

    qs = (
        qs.select_related(
            "organization",
            "statement",
            "deadline",
        )
        .prefetch_related(
            Prefetch(
                "report_items",
                queryset=(
                    ReportItem.objects
                    .select_related("statement_column", "statement_column__parent")
                    .prefetch_related("inners")
                ),
            )
        )
        .order_by("organization__name")
    )

    return qs



def _safe_decimal(v) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _build_statement_maps(statement) -> Tuple[Dict[str, StatementColumn], Dict[str, List[StatementColumn]]]:
    cols = list(
        StatementColumn.objects
        .filter(statement=statement)
        .select_related("parent")
        .only("id", "parent_id", "ordering", "title_uz", "title_ru", "is_organization")
    )
    by_id = {str(c.id): c for c in cols}
    by_parent: Dict[str | None, List[StatementColumn]] = defaultdict(list)
    for c in cols:
        by_parent[str(c.parent_id) if c.parent_id else None].append(c)
    # sort children by ordering
    for k in by_parent:
        by_parent[k].sort(key=lambda c: [int(p) if p.isdigit() else p for p in (c.ordering or "").split(".")])
    return by_id, by_parent


def _full_column_path(col: StatementColumn, by_id: Dict[str, StatementColumn], lang: str) -> str:
    """Build full path: parent → child → leaf joined with " – "."""
    parts: List[str] = []
    cur = col
    while cur is not None:
        title = get_translated_field(cur, "title", lang) or ""
        parts.append(title)
        pid = getattr(cur, "parent_id", None)
        cur = by_id.get(str(pid)) if pid else None
    parts.reverse()
    return " – ".join([p for p in parts if p])


def _is_org_name_column(col: StatementColumn) -> bool:
    # True if flagged or title matches common org-name labels in uz/ru
    try:
        if getattr(col, "is_organization", False):
            return True
    except Exception:
        pass
    titles = [
        (getattr(col, "title_uz", "") or "").strip().lower(),
        (getattr(col, "title_ru", "") or "").strip().lower(),
    ]
    keys = [
        "tashkilot nomi",
        "наименование организации",
        "название организации",
    ]
    return any(any(k in t for k in keys) for t in titles)


def _sum_by_column(items: List[ReportItem]) -> Dict[str, Decimal]:
    """Sum numeric inners per statement_column_id."""
    total: Dict[str, Decimal] = defaultdict(Decimal)
    for it in items:
        cid = str(it.statement_column_id)
        for inn in it.inners.all():
            total[cid] += _safe_decimal(inn.value)
    return total


def build_region_snapshot(region, reports: List[Report], lang: str) -> Dict:
    """
    Build a region-level Jami block similar to ReportListSerializer output (single block in report_items).
    """
    if not reports:
        return {
            "id": "general",
            "organization": None,
            "organization_name": f"{region} – Viloyat Jami",
            "statement": None,
            "deadline": None,
            "period": None,
            "status": None,
            "report_items": [
                {
                    "organization_id": "general",
                    "organization_name": f"{region} – Viloyat Jami",
                    "statement_columns": [],
                }
            ],
            "is_general": True,
            "is_individual_general": False,
            "is_republic": False,
        }

    statement = reports[0].statement
    by_id, _ = _build_statement_maps(statement)

    # aggregate per column and per plant
    # totals[cid][plant_id_or_None] = Decimal
    totals: Dict[str, Dict[str | None, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for rep in reports:
        for it in rep.report_items.all():
            cid = str(it.statement_column_id)
            for inn in it.inners.all():
                plant_key = str(inn.plant_id) if inn.plant_id else None
                totals[cid][plant_key] += _safe_decimal(inn.value)

    # collect plant ids for map
    plant_ids = {pid for per_plant in totals.values() for pid in per_plant.keys() if pid}
    plant_map = {str(pid): name for pid, name in Plant.objects.filter(id__in=plant_ids).values_list("id", "name")}

    # build columns list
    cols_payload = []
    for cid, per_plant in totals.items():
        col = by_id.get(cid)
        if not col:
            continue
        # Organization name columns: show region jami label, do not split by plant
        if _is_org_name_column(col):
            region_label = dict(RegionChoices.choices).get(str(region), str(region))
            cols_payload.append({
                "statement_column_id": cid,
                "statement_column_name": _full_column_path(col, by_id, lang),
                "inners": [{
                    "value": f"{region_label} – Viloyat Jami",
                }],
            })
            continue

        inners = []
        # stable order: plants (by name) then None
        plant_keys_sorted = sorted([k for k in per_plant.keys() if k], key=lambda k: plant_map.get(k, ""))
        for pk in plant_keys_sorted:
            inners.append({
                "plant_id": pk,
                "plant_name": plant_map.get(pk, ""),
                "value": str(per_plant[pk]),
            })
        if None in per_plant:
            inners.append({
                "value": str(per_plant[None]),
            })
        cols_payload.append({
            "statement_column_id": cid,
            "statement_column_name": _full_column_path(col, by_id, lang),
            "inners": inners,
        })

    return {
        "id": "general",
        "organization": None,
        "organization_name": f"{region} – Viloyat Jami",
        "statement": str(statement.id),
        "deadline": None,
        "period": None,
        "status": "saved",
        "report_items": [
            {
                "organization_id": "general",
                "organization_name": f"{region} – Viloyat Jami",
                "statement_columns": cols_payload,
            }
        ],
        "is_general": True,
        "is_individual_general": False,
        "is_republic": False,
    }


def build_republic_snapshot(reports: List[Report], lang: str) -> Dict:
    if not reports:
        return {
            "id": "republic",
            "organization": None,
            "organization_name": "Respublika Jami",
            "statement": None,
            "deadline": None,
            "period": None,
            "status": None,
            "report_items": [
                {
                    "organization_id": "republic",
                    "organization_name": "Respublika Jami",
                    "statement_columns": [],
                }
            ],
            "is_general": False,
            "is_individual_general": False,
            "is_republic": True,
        }

    statement = reports[0].statement
    by_id, _ = _build_statement_maps(statement)

    totals: Dict[str, Dict[str | None, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for rep in reports:
        for it in rep.report_items.all():
            cid = str(it.statement_column_id)
            for inn in it.inners.all():
                plant_key = str(inn.plant_id) if inn.plant_id else None
                totals[cid][plant_key] += _safe_decimal(inn.value)

    plant_ids = {pid for per_plant in totals.values() for pid in per_plant.keys() if pid}
    plant_map = {str(pid): name for pid, name in Plant.objects.filter(id__in=plant_ids).values_list("id", "name")}

    cols_payload = []
    for cid, per_plant in totals.items():
        col = by_id.get(cid)
        if not col:
            continue
        # Organization name columns: show Republic Jami label, do not split by plant
        if _is_org_name_column(col):
            cols_payload.append({
                "statement_column_id": cid,
                "statement_column_name": _full_column_path(col, by_id, lang),
                "inners": [{
                    "value": "Respublika Jami",
                }],
            })
            continue

        inners = []
        plant_keys_sorted = sorted([k for k in per_plant.keys() if k], key=lambda k: plant_map.get(k, ""))
        for pk in plant_keys_sorted:
            inners.append({
                "plant_id": pk,
                "plant_name": plant_map.get(pk, ""),
                "value": str(per_plant[pk]),
            })
        if None in per_plant:
            inners.append({
                "value": str(per_plant[None]),
            })
        cols_payload.append({
            "statement_column_id": cid,
            "statement_column_name": _full_column_path(col, by_id, lang),
            "inners": inners,
        })

    return {
        "id": "republic",
        "organization": None,
        "organization_name": "Respublika Jami",
        "statement": str(statement.id),
        "deadline": None,
        "period": None,
        "status": "saved",
        "report_items": [
            {
                "organization_id": "republic",
                "organization_name": "Respublika Jami",
                "statement_columns": cols_payload,
            }
        ],
        "is_general": False,
        "is_individual_general": False,
        "is_republic": True,
    }


def build_filtered_payload(statement, deadline_id: str, lang: str) -> Dict:
    """
    Returns a payload with:
      - regions: [ { region, general (region jami), organizations: [ReportListSerializer-like dicts for individuals] } ]
      - republic: republic jami snapshot
    """
    qs = filter_reports_by_period(statement, deadline_id)

    # Materialize individuals for reuse and avoid repeated DB hits
    reports = list(qs)

    # Build region -> reports mapping
    by_region: Dict[str, List[Report]] = defaultdict(list)
    for rep in reports:
        key = str(getattr(rep, "region", ""))
        by_region[key].append(rep)

    # Preload statement columns once for full-path naming
    cols = list(
        StatementColumn.objects
        .filter(statement_id=str(statement.id))
        .select_related("parent")
        .only("id", "parent_id", "ordering", "title_uz", "title_ru", "is_organization", "statement_id")
    )
    by_id = {str(c.id): c for c in cols}

    # Collect all plant ids used across reports for organization-level serialization
    plant_ids_all: set[str] = set()
    for rep in reports:
        for it in rep.report_items.all():
            for inn in it.inners.all():
                if inn.plant_id:
                    plant_ids_all.add(str(inn.plant_id))
    plant_map_all = {str(pid): name for pid, name in Plant.objects.filter(id__in=plant_ids_all).values_list("id", "name")}

    def serialize_individual(rep: Report) -> Dict:
        # Aggregate per column and plant for a single organization
        totals: Dict[str, Dict[str | None, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
        for it in rep.report_items.all():
            cid = str(it.statement_column_id)
            for inn in it.inners.all():
                plant_key = str(inn.plant_id) if inn.plant_id else None
                totals[cid][plant_key] += _safe_decimal(inn.value)

        # Resolve organization name once (used in org-name columns below)
        org_name = get_translated_field(rep.organization, "name", lang) if getattr(rep, "organization", None) else ""

        statement_columns = []
        for cid, per_plant in totals.items():
            col = by_id.get(cid)
            if not col:
                continue
            # Organization name columns: show organization name; no plant split
            if _is_org_name_column(col):
                statement_columns.append({
                    "statement_column_id": cid,
                    "statement_column_name": _full_column_path(col, by_id, lang),
                    "inners": [{
                        "value": org_name,
                    }],
                })
                continue

            inners = []
            # stable plant order
            plant_keys_sorted = sorted([k for k in per_plant.keys() if k], key=lambda k: plant_map_all.get(k, ""))
            for pk in plant_keys_sorted:
                inners.append({
                    "plant_id": pk,
                    "plant_name": plant_map_all.get(pk, ""),
                    "value": str(per_plant[pk]),
                })
            if None in per_plant:
                inners.append({
                    "value": str(per_plant[None]),
                })
            statement_columns.append({
                "statement_column_id": cid,
                "statement_column_name": _full_column_path(col, by_id, lang),
                "inners": inners,
            })

        return {
            "id": str(rep.id),
            "organization": str(getattr(rep.organization, "id", "")) if rep.organization else None,
            "organization_name": org_name,
            "statement": str(rep.statement_id),
            "deadline": str(rep.deadline_id) if getattr(rep, "deadline_id", None) else None,
            "report_items": [
                {
                    "organization_id": str(getattr(rep.organization, "id", "")) if rep.organization else None,
                    "organization_name": org_name,
                    "statement_columns": statement_columns,
                }
            ],
            "is_general": False,
            "is_individual_general": False,
            "is_republic": False,
        }

    regions_payload = []
    for region_key, reps in by_region.items():
        # individual orgs (plant-aware, read-only)
        orgs_payload = [serialize_individual(rep) for rep in reps]

        # region jami snapshot from filtered reps
        region_snapshot = build_region_snapshot(region_key, reps, lang)
        regions_payload.append({
            "region": region_key,
            "general": region_snapshot,
            "organizations": orgs_payload,
        })

    # republic jami from all filtered individuals
    republic_snapshot = build_republic_snapshot(reports, lang)

    return {
        "regions": regions_payload,
        "republic": republic_snapshot,
    }
