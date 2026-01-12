from collections import defaultdict, OrderedDict
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from apps.reports.models import Report, Statement, StatementColumn
from apps.utils.services import RegionChoices
from apps.reports.models import Plant
from apps.reports.services.normalize_utils import normalize
from apps.utils.translation import get_translated_field
from django.utils import translation


Number = Decimal


def _safe_decimal(val) -> Number:
    try:
        return Decimal(str(val or 0))
    except Exception:
        return Decimal(0)


def _collect_org_general_reports(statement: Statement) -> List[Report]:
    """
    Use per-organization general reports as the canonical source
    (is_individual_general=True, is_report=False), as they are recalculated
    on each acceptance and contain consolidated inners including plant split.
    """
    return list(
        Report.objects.filter(
            statement=statement,
            is_report=True,
            is_plant_based=True,
            status=Report.StatusChoices.ACCEPTED,
        )
        .select_related("organization")
        .prefetch_related("report_items__statement_column", "report_items__inners__plant")
    )


def _sum_values_by_plant_and_column(org_reports: List[Report]) -> Dict[Tuple[str, str, str], Number]:
    """
    Build totals keyed by (org_id, plant_id, column_id) -> Decimal
    Only inners with a non-null plant are considered.
    """
    totals: Dict[Tuple[str, str, str], Number] = defaultdict(Decimal)
    for rep in org_reports:
        org_id = str(getattr(rep.organization, 'id', '')) if rep.organization else None
        if not org_id:
            continue
        for item in rep.report_items.all():
            col_id = str(item.statement_column_id)
            for inner in item.inners.all():
                if not inner.plant_id:
                    continue
                key = (org_id, str(inner.plant_id), col_id)
                totals[key] += _safe_decimal(inner.value)
    return totals


def _columns_for_statement(statement: Statement) -> list[StatementColumn]:
    """
    Return ONLY leaf (childless) columns for the statement.
    """
    return list(
        StatementColumn.objects
        .filter(
            statement=statement,
            children__isnull=True
        )
        .order_by("ordering")
        .distinct()
    )


def _build_column_meta(columns: List[StatementColumn], lang: str) -> Dict[str, Dict[str, str]]:
    meta: Dict[str, Dict[str, str]] = {}
    for c in columns:
        cid = str(c.id)
        ordering = c.ordering or "0"
        meta[cid] = {
            "id": cid,
            "ordering": ordering,
            "key": ordering.replace(".", "_"),
            "name": get_translated_field(c, "title", lang),
        }
    return meta


def _format_variant_b(values_map: Dict[str, Number], col_meta: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """
    Convert column_id -> Decimal into Variant B structure:
    column_id -> { id, key, ordering, name, value }
    Keep UUID keys stable and omit unknown columns defensively.
    """
    out: Dict[str, Dict[str, str]] = {}
    for cid, total in values_map.items():
        meta = col_meta.get(cid)
        if not meta:
            continue
        out[cid] = {
            **meta,
            "value": normalize(total),
        }
    return out


def build_plant_svodka(statement: Statement, plant: Optional[Plant] = None, include_empty: bool = True, lang: str = "uz"):
    """
    Compute plant-based hierarchical svodka without persisting.

    Response format per plant:
    {
      "plant": Plant.name,
      "rows": [
          {"level": "region", "name": <region_name>, "depth": 0, "values": {col_id: sum, ...}},
          {"level": "organization", "name": <org_name>, "depth": 1, "values": {...}},
          ...,
          {"level": "republic", "name": "Respublika Jami", "depth": 0, "values": {...}}
      ]
    }
    """
    # 1) Select plants
    if plant:
        plants = [plant]
    else:
        plants = list(Plant.objects.filter(statement=statement).order_by("name"))
        if not plants:
            # fallback to all plants if not bound to statement
            plants = list(Plant.objects.filter(statement__isnull=True).order_by("name"))

    # 2) Source reports: per-organization general reports
    org_reports = _collect_org_general_reports(statement)
    if not org_reports:
        return []

    # 3) Precompute totals by org/plant/column
    opc_totals = _sum_values_by_plant_and_column(org_reports)

    # 4) Build organization metadata map
    from apps.general.models import Organization
    org_ids = {k[0] for k in opc_totals.keys()}
    org_map: Dict[str, Organization] = {
        str(o.id): o for o in Organization.objects.filter(id__in=org_ids)
    }

    # 5) Statement columns to include and metadata
    columns = _columns_for_statement(statement)
    column_ids = [str(c.id) for c in columns]
    col_meta = _build_column_meta(columns, lang)

    result = []

    # Helper to init value dict with zeros for consistent ordering
    def zero_values() -> Dict[str, Number]:
        return {cid: Decimal(0) for cid in column_ids}

    # Region display names not required as we iterate choices directly

    for p in plants:
        # per-plant rows accumulator
        region_rows: Dict[str, Dict] = OrderedDict()  # region -> row dict
        org_rows: List[Dict] = []
        republic_values: Dict[str, Number] = zero_values()

        # First, accumulate per-org totals for this plant

        # Build a quick per-org per-plant per-col matrix for current plant
        per_org_values: Dict[str, Dict[str, Number]] = defaultdict(lambda: zero_values())
        per_org_name: Dict[str, str] = {}
        per_org_region: Dict[str, str] = {}

        for (org_id, plant_id, col_id), value in opc_totals.items():
            if plant_id != str(p.id):
                continue
            org = org_map.get(org_id)
            if not org:
                continue
            per_org_values[org_id][col_id] += value
            per_org_name[org_id] = get_translated_field(org, 'name', lang) or str(org_id)
            per_org_region[org_id] = org.region

        # Assemble rows per region in a stable region order based on choices
        # Only include regions that have at least one org row
        has_any_org = False
        for reg_code, reg_label in RegionChoices.choices:
            # skip republic pseudo region
            if reg_code == RegionChoices.REPUBLIC:
                continue
            # collect orgs of this region
            orgs_here = [oid for oid, r in per_org_region.items() if r == reg_code]
            if not orgs_here:
                continue
            has_any_org = True
            # region accumulator
            region_vals: Dict[str, Number] = zero_values()
            # add region header row placeholder (will append after org children)
            with translation.override(lang):
                region_rows[reg_code] = {
                    "level": "region",
                    "name": str(reg_label),
                    "depth": 0,
                    "values": None,  # fill later
                }
            # org child rows
            for oid in sorted(orgs_here, key=lambda x: per_org_name.get(x, "")):
                vals = per_org_values.get(oid, zero_values())
                # accumulate to region and republic
                for cid in column_ids:
                    region_vals[cid] += vals.get(cid, Decimal(0))
                    republic_values[cid] += vals.get(cid, Decimal(0))
                org_rows.append({
                    "level": "organization",
                    "name": per_org_name.get(oid, oid),
                    "depth": 1,
                    "values": _format_variant_b(vals, col_meta),
                })
            # finalize region header values
            region_rows[reg_code]["values"] = _format_variant_b(region_vals, col_meta)

        # Build final rows deterministically by RegionChoices order
        rows = []
        for reg_code, reg_label in RegionChoices.choices:
            if reg_code == RegionChoices.REPUBLIC:
                continue
            orgs_here = [oid for oid, r in per_org_region.items() if r == reg_code]
            if not orgs_here:
                continue
            # append region header
            rows.append(region_rows[reg_code])
            # append its orgs
            for oid in sorted(orgs_here, key=lambda x: per_org_name.get(x, "")):
                vals = per_org_values.get(oid, zero_values())
                rows.append({
                    "level": "organization",
                    "name": per_org_name.get(oid, oid),
                    "depth": 1,
                    "values": _format_variant_b(vals, col_meta),
                })

        # finally republic row
        with translation.override(lang):
            rows.append({
                "level": "republic",
                "name": "Respublika Jami",
                "depth": 0,
                "values": _format_variant_b(republic_values, col_meta),
            })

        # Exclude empty plants if requested (when plant filter is applied)
        if include_empty or has_any_org:
            result.append({
                "plant": get_translated_field(p, 'name', lang),
                "rows": rows,
            })

    return result
