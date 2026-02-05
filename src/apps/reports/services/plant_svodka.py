from collections import defaultdict, OrderedDict
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from apps.reports.models import Report, Statement, StatementColumn
from apps.utils.services import RegionChoices
from apps.reports.models import Plant
from apps.reports.services.normalize_utils import normalize
from apps.utils.translation import get_translated_field
from django.utils import translation
from django.db.models import Q


Number = Decimal


def _safe_decimal(val) -> Number:
    try:
        return Decimal(str(val or 0))
    except Exception:
        return Decimal(0)


def _collect_org_general_reports(statement: Statement, deadline) -> List[Report]:
    """
    Only ACCEPTED plant-based reports created for this deadline.
    This is the ONLY source of truth for plant svodka.
    """

    return list(
        Report.objects.filter(
            statement=statement,
            deadline=deadline,
            is_plant_based=True,
            status=Report.StatusChoices.ACCEPTED,
        )
        .select_related("organization")
        .prefetch_related("report_items__inners__plant")
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


def _preload_columns_structure(statement: Statement) -> Tuple[
    List[str],  # ordered leaf ids
    Dict[str, Dict[str, object]],  # col_meta_by_id: id -> {id, ordering, name_uz, name_ru, is_organization, parent_id, statement_id}
    Dict[str, str],  # parent_map: id -> parent_id
    Dict[str, str],  # title_map_uz: id -> title_uz
    Dict[str, str],  # title_map_ru: id -> title_ru
]:
    """
    Load all columns related to the statement in ONE query and build in-memory maps.
    The queryset returns both leaves (statement=statement) and their ancestors
    (columns that have children with statement=statement).
    Leaf detection and root traversal are done purely in Python using parent_id.
    """
    qs = (
        StatementColumn.objects
        .filter(Q(statement=statement) | Q(children__statement=statement))
        .only("id", "parent_id", "ordering", "title_uz", "title_ru", "is_organization", "statement_id")
        .distinct()
    )

    col_meta_by_id: Dict[str, Dict[str, object]] = {}
    parent_map: Dict[str, Optional[str]] = {}
    title_map_uz: Dict[str, str] = {}
    title_map_ru: Dict[str, str] = {}
    children_index: Dict[Optional[str], List[str]] = defaultdict(list)

    stmt_id_str = str(statement.id)
    for c in qs:
        cid = str(c.id)
        pid = str(c.parent_id) if c.parent_id else None
        parent_map[cid] = pid
        title_map_uz[cid] = getattr(c, "title_uz", "")
        title_map_ru[cid] = getattr(c, "title_ru", "")
        col_meta_by_id[cid] = {
            "id": cid,
            "ordering": c.ordering or "0",
            "is_organization": bool(getattr(c, "is_organization", False)),
            "parent_id": pid,
            "statement_id": str(c.statement_id) if c.statement_id else None,
        }
        children_index[pid].append(cid)

    # Leaves: columns that belong to this statement AND have no children among the loaded set
    leaf_ids = [
        cid for cid, meta in col_meta_by_id.items()
        if meta.get("statement_id") == stmt_id_str and cid not in children_index
    ]

    # Order leaves by their ordering value (string with dotted parts), compare lexicographically
    leaf_ids.sort(key=lambda x: col_meta_by_id[x]["ordering"])

    return leaf_ids, col_meta_by_id, parent_map, title_map_uz, title_map_ru


def _build_column_meta_from_maps(
    leaf_ids: List[str],
    col_meta_by_id: Dict[str, Dict[str, object]],
    title_map_uz: Dict[str, str],
    title_map_ru: Dict[str, str],
    lang: str,
) -> Dict[str, Dict[str, str]]:
    meta: Dict[str, Dict[str, str]] = {}
    for cid in leaf_ids:
        base = col_meta_by_id[cid]
        ordering = base["ordering"]
        title = title_map_uz[cid] if lang == "uz" else title_map_ru[cid]
        meta[cid] = {
            "id": cid,
            "ordering": ordering,
            "key": ordering.replace(".", "_"),
            "name": title,
            "is_organization": bool(base.get("is_organization", False)),
            "appendix_id": None,
            "appendix_name": None,
        }
    return meta


def _root_appendix_id(col_id: str, parent_map: Dict[str, Optional[str]]) -> str:
    cur = col_id
    while parent_map.get(cur):
        cur = parent_map[cur]  # type: ignore[index]
    return cur


def _group_columns_by_appendix_ids(
    leaf_ids: List[str],
    parent_map: Dict[str, Optional[str]],
    title_map_uz: Dict[str, str],
    title_map_ru: Dict[str, str],
    lang: str,
) -> Tuple[Dict[str, List[str]], Dict[str, Dict[str, str]]]:
    """
    Returns:
    - mapping appendix_id -> ordered list of leaf column ids under it
    - mapping appendix_id -> {appendix_id, appendix_name}
    All computed with pure Python parent_map traversal.
    """
    by_app: Dict[str, List[str]] = OrderedDict()
    appendix_meta: Dict[str, Dict[str, str]] = {}
    for cid in leaf_ids:
        aid = _root_appendix_id(cid, parent_map)
        if aid not in by_app:
            by_app[aid] = []
            app_name = title_map_uz.get(aid, "") if lang == "uz" else title_map_ru.get(aid, "")
            appendix_meta[aid] = {
                "appendix_id": aid,
                "appendix_name": app_name,
            }
        by_app[aid].append(cid)
    return by_app, appendix_meta


def _format_statement_columns(
    col_ids: List[str],
    values_map: Dict[str, Number],
    col_meta: Dict[str, Dict[str, str]],
    *,
    org_name_for_special: Optional[str] = None,
    region_name_for_special: Optional[str] = None,
    is_republic: bool = False,
) -> List[Dict[str, object]]:
    """
    Build ordered list of statement_columns for a row. Handles special case for
    the 'Tashkilot nomi' column (is_organization=True) replacing numeric value
    with the appropriate string.
    """
    out: List[Dict[str, object]] = []
    for cid in col_ids:
        meta = col_meta.get(cid)
        if not meta:
            continue
        value: object
        if meta.get("is_organization"):
            if is_republic:
                value = "Respublika Jami"
            elif region_name_for_special is not None:
                value = f"{region_name_for_special} – Viloyat Jami"
            else:
                value = org_name_for_special or ""
        else:
            value = normalize(values_map.get(cid, Decimal(0)))
        out.append({
            "statement_column_id": meta["id"],
            "ordering": meta["ordering"],
            "name": meta["name"],
            "value": value,
        })
    return out


def build_plant_svodka(statement: Statement, deadline, plant: Optional[Plant] = None, include_empty: bool = True, lang: str = "uz"):
    """
    Build appendix-separated, hierarchical svodka aggregated by plant.

    Top-level per-plant structure:
    {
      "statement": {"id": str, "name": str},
      "plant": {"id": str, "name": str},
      "appendices": [
          {
            "appendix_id": str,
            "appendix_name": str,
            "rows": [
                {"level": "organization"|"region"|"republic", "depth": 2|1|0,
                 "organization_id": str|null, "organization_name": str,
                 "statement_columns": [{"statement_column_id", "ordering", "name", "value"}, ...]}
            ]
          }, ...
      ]
    }
    """
    # 1) Select plants
    if plant:
        plants = [plant]
    else:
        plants = list(Plant.objects.filter(statement=statement).order_by("name"))
        if not plants:
            plants = list(Plant.objects.filter(statement__isnull=True).order_by("name"))

    # 2) Source reports: per-organization, plant-based accepted reports
    org_reports = _collect_org_general_reports(statement, deadline)
    if not org_reports:
        return []

    # 3) Precompute totals by (org_id, plant_id, col_id)
    opc_totals = _sum_values_by_plant_and_column(org_reports)

    # 4) Organizations metadata
    from apps.general.models import Organization
    org_ids = {k[0] for k in opc_totals.keys()}
    org_map: Dict[str, Organization] = {
        str(o.id): o for o in Organization.objects.filter(id__in=org_ids)
    }

    # 5) Columns and metadata, grouped by appendix (all preloaded at once)
    leaf_ids, col_meta_by_id, parent_map, title_map_uz, title_map_ru = _preload_columns_structure(statement)
    col_meta = _build_column_meta_from_maps(leaf_ids, col_meta_by_id, title_map_uz, title_map_ru, lang)

    by_app, appendix_meta = _group_columns_by_appendix_ids(leaf_ids, parent_map, title_map_uz, title_map_ru, lang)
    for aid, col_ids in by_app.items():
        app_name = appendix_meta[aid]["appendix_name"]
        for cid in col_ids:
            if cid in col_meta:
                col_meta[cid]["appendix_id"] = aid
                col_meta[cid]["appendix_name"] = app_name

    result: List[Dict] = []

    # helper zeros
    def zero_values_for(col_ids: List[str]) -> Dict[str, Number]:
        return {cid: Decimal(0) for cid in col_ids}

    # Statement meta
    statement_meta = {
        "id": str(statement.id),
        "name": get_translated_field(statement, "name", lang),
    }

    for p in plants:
        plant_meta = {"id": str(p.id), "name": get_translated_field(p, "name", lang)}

        # Build per-org matrix limited to this plant
        per_org_values: Dict[str, Dict[str, Number]] = defaultdict(dict)
        per_org_name: Dict[str, str] = {}
        per_org_region: Dict[str, str] = {}

        # initialize dicts lazily to avoid large zero maps for all cols
        for (org_id, plant_id, col_id), value in opc_totals.items():
            if plant_id != str(p.id):
                continue
            org = org_map.get(org_id)
            if not org:
                continue
            if org_id not in per_org_values:
                per_org_values[org_id] = {}
            per_org_values[org_id][col_id] = per_org_values[org_id].get(col_id, Decimal(0)) + value
            per_org_name[org_id] = get_translated_field(org, "name", lang) or str(org_id)
            per_org_region[org_id] = org.region

        has_any_org = bool(per_org_values)
        if plant and not has_any_org:
            return {"detail": "Ushbu muddatda tanlangan plant haqida ma'lumot yo'q"}

        # Build the ONE global row set (shared across appendices)
        base_rows: List[Dict] = []

        # 1) Organization rows (sorted by region then org name) with full values map
        for reg_code, _ in RegionChoices.choices:
            if reg_code == RegionChoices.REPUBLIC:
                continue
            orgs_here = [oid for oid, r in per_org_region.items() if r == reg_code]
            for oid in sorted(orgs_here, key=lambda x: per_org_name.get(x, "")):
                base_rows.append({
                    "level": "organization",
                    "depth": 2,
                    "organization_id": oid,
                    "organization_name": per_org_name.get(oid, oid),
                    "_all_values": per_org_values.get(oid, {}),  # all columns
                    "_region_code": reg_code,
                })

        # 2) Region rows (one per region with any orgs), full values map aggregated once
        for reg_code, reg_label in RegionChoices.choices:
            if reg_code == RegionChoices.REPUBLIC:
                continue
            orgs_here = [oid for oid, r in per_org_region.items() if r == reg_code]
            if not orgs_here:
                continue
            region_values: Dict[str, Number] = {}
            for oid in orgs_here:
                src = per_org_values.get(oid, {})
                for cid, val in src.items():
                    region_values[cid] = region_values.get(cid, Decimal(0)) + val
            with translation.override(lang):
                region_name = str(reg_label)
            base_rows.append({
                "level": "region",
                "depth": 1,
                "organization_id": None,
                "organization_name": f"{region_name} – Viloyat Jami",
                "_all_values": region_values,
                "_region_name": region_name,
                "_region_code": reg_code,
            })

        # 3) Republic row (single), full values map aggregated once
        republic_values: Dict[str, Number] = {}
        for oid, src in per_org_values.items():
            for cid, val in src.items():
                republic_values[cid] = republic_values.get(cid, Decimal(0)) + val
        base_rows.append({
            "level": "republic",
            "depth": 0,
            "organization_id": None,
            "organization_name": "Respublika Jami",
            "_all_values": republic_values,
        })

        # Now serialize appendices by slicing columns from the shared rows
        appendices_block: List[Dict] = []
        for appendix_id, appendix_info in appendix_meta.items():
            col_ids = by_app.get(appendix_id, [])
            if not col_ids:
                continue
            rows: List[Dict] = []
            for r in base_rows:
                values_map = r.get("_all_values", {})
                level = r["level"]
                # Determine special text context
                org_name = r.get("organization_name") if level == "organization" else None
                region_name = r.get("_region_name") if level == "region" else None
                is_republic = level == "republic"
                rows.append({
                    "level": level,
                    "depth": r["depth"],
                    "organization_id": r.get("organization_id"),
                    "organization_name": r.get("organization_name"),
                    "statement_columns": _format_statement_columns(
                        col_ids,
                        values_map,
                        col_meta,
                        org_name_for_special=org_name,
                        region_name_for_special=region_name,
                        is_republic=is_republic,
                    ),
                })
            if include_empty or has_any_org:
                appendices_block.append({
                    "appendix_id": appendix_info["appendix_id"],
                    "appendix_name": appendix_info["appendix_name"],
                    "rows": rows,
                })

        if include_empty or has_any_org:
            result.append({
                "statement": statement_meta,
                "plant": plant_meta,
                "appendices": appendices_block,
            })

    # If only one plant requested, return single object for convenience
    if plant and result:
        return result[0]
    return result


# ---------------- NEW: PURE-PYTHON BUILDER FROM PRELOADED DATA ----------------

def build_plant_svodka_from_preloaded(
    *,
    statement_id: str,
    columns: List[StatementColumn],
    reports: List[Report],
    plants: List[Plant],
    lang: str = "uz",
) -> List[Dict]:
    """
    Pure Python projection that builds plant-based svodka using already preloaded
    datasets. This function performs ZERO ORM queries and must be fed with:
    - columns: StatementColumn objects for this statement (with parent prefetched)
    - reports: ACCEPTED plant-based org-level reports with report_items+inners prefetched
    - plants: Plant objects for this statement
    """
    # Columns metadata maps (no queries)
    col_meta_by_id: Dict[str, Dict[str, object]] = {}
    parent_map: Dict[str, Optional[str]] = {}
    title_map_uz: Dict[str, str] = {}
    title_map_ru: Dict[str, str] = {}
    children_index: Dict[Optional[str], List[str]] = defaultdict(list)

    stmt_id_str = str(statement_id)
    for c in columns:
        cid = str(c.id)
        pid = str(c.parent_id) if c.parent_id else None
        parent_map[cid] = pid
        title_map_uz[cid] = getattr(c, "title_uz", "")
        title_map_ru[cid] = getattr(c, "title_ru", "")
        col_meta_by_id[cid] = {
            "id": cid,
            "ordering": c.ordering or "0",
            "is_organization": bool(getattr(c, "is_organization", False)),
            "parent_id": pid,
            "statement_id": str(getattr(c, "statement_id", None)) if getattr(c, "statement_id", None) else None,
        }
        children_index[pid].append(cid)

    # Leaves: columns that belong to this statement AND have no children among the loaded set
    leaf_ids = [
        cid for cid, meta in col_meta_by_id.items()
        if meta.get("statement_id") == stmt_id_str and cid not in children_index
    ]
    leaf_ids.sort(key=lambda x: col_meta_by_id[x]["ordering"])  # Python ordering

    # Column meta projection for serialization
    col_meta = _build_column_meta_from_maps(leaf_ids, col_meta_by_id, title_map_uz, title_map_ru, lang)

    # Group leaves by appendix (root parent traversal in Python)
    by_app, appendix_meta = _group_columns_by_appendix_ids(leaf_ids, parent_map, title_map_uz, title_map_ru, lang)
    for aid, col_ids in by_app.items():
        app_name = appendix_meta[aid]["appendix_name"]
        for cid in col_ids:
            if cid in col_meta:
                col_meta[cid]["appendix_id"] = aid
                col_meta[cid]["appendix_name"] = app_name

    # Build totals by (org_id, plant_id, col_id) from preloaded reports
    opc_totals: Dict[Tuple[str, str, str], Number] = defaultdict(Decimal)
    org_map: Dict[str, object] = {}
    for rep in reports:
        if not rep.organization:
            continue
        org_id = str(rep.organization.id)
        org_map[org_id] = rep.organization
        for item in rep.report_items.all():
            col_id = str(item.statement_column_id)
            for inner in item.inners.all():
                if not inner.plant_id:
                    continue
                key = (org_id, str(inner.plant_id), col_id)
                opc_totals[key] += _safe_decimal(inner.value)

    # Statement meta (lightweight)
    from apps.reports.models import Statement  # type: ignore
    statement_meta = {"id": stmt_id_str}

    # Prepare plants list (input already preloaded)
    result: List[Dict] = []
    for p in plants:
        plant_meta = {"id": str(p.id), "name": get_translated_field(p, "name", lang)}

        # Build per-org matrices limited to this plant
        per_org_values: Dict[str, Dict[str, Number]] = defaultdict(dict)
        per_org_name: Dict[str, str] = {}
        per_org_region: Dict[str, str] = {}

        for (org_id, plant_id, col_id), value in opc_totals.items():
            if plant_id != str(p.id):
                continue
            org = org_map.get(org_id)
            if not org:
                continue
            if org_id not in per_org_values:
                per_org_values[org_id] = {}
            per_org_values[org_id][col_id] = per_org_values[org_id].get(col_id, Decimal(0)) + value
            per_org_name[org_id] = get_translated_field(org, "name", lang) or str(org_id)
            per_org_region[org_id] = getattr(org, "region", None)

        has_any_org = bool(per_org_values)

        # Build shared base rows
        base_rows: List[Dict] = []
        from apps.utils.services import RegionChoices  # type: ignore
        from django.utils import translation as _tr

        # Organization rows
        for reg_code, _ in RegionChoices.choices:
            if reg_code == RegionChoices.REPUBLIC:
                continue
            orgs_here = [oid for oid, r in per_org_region.items() if r == reg_code]
            for oid in sorted(orgs_here, key=lambda x: per_org_name.get(x, "")):
                base_rows.append({
                    "level": "organization",
                    "depth": 2,
                    "organization_id": oid,
                    "organization_name": per_org_name.get(oid, oid),
                    "_all_values": per_org_values.get(oid, {}),
                    "_region_code": reg_code,
                })

        # Region rows
        for reg_code, reg_label in RegionChoices.choices:
            if reg_code == RegionChoices.REPUBLIC:
                continue
            orgs_here = [oid for oid, r in per_org_region.items() if r == reg_code]
            if not orgs_here:
                continue
            region_values: Dict[str, Number] = {}
            for oid in orgs_here:
                src = per_org_values.get(oid, {})
                for cid, val in src.items():
                    region_values[cid] = region_values.get(cid, Decimal(0)) + val
            with _tr.override(lang):
                region_name = str(reg_label)
            base_rows.append({
                "level": "region",
                "depth": 1,
                "organization_id": None,
                "organization_name": f"{region_name} – Viloyat Jami",
                "_all_values": region_values,
                "_region_name": region_name,
                "_region_code": reg_code,
            })

        # Republic row
        republic_values: Dict[str, Number] = {}
        for _, src in per_org_values.items():
            for cid, val in src.items():
                republic_values[cid] = republic_values.get(cid, Decimal(0)) + val
        base_rows.append({
            "level": "republic",
            "depth": 0,
            "organization_id": None,
            "organization_name": "Respublika Jami",
            "_all_values": republic_values,
        })

        # Serialize appendices
        appendices_block: List[Dict] = []
        for appendix_id, appendix_info in appendix_meta.items():
            col_ids = by_app.get(appendix_id, [])
            if not col_ids:
                continue
            rows: List[Dict] = []
            for r in base_rows:
                values_map = r.get("_all_values", {})
                level = r["level"]
                org_name = r.get("organization_name") if level == "organization" else None
                region_name = r.get("_region_name") if level == "region" else None
                is_republic = level == "republic"
                rows.append({
                    "level": level,
                    "depth": r["depth"],
                    "organization_id": r.get("organization_id"),
                    "organization_name": r.get("organization_name"),
                    "statement_columns": _format_statement_columns(
                        col_ids,
                        values_map,
                        col_meta,
                        org_name_for_special=org_name,
                        region_name_for_special=region_name,
                        is_republic=is_republic,
                    ),
                })
            appendices_block.append({
                "appendix_id": appendix_info["appendix_id"],
                "appendix_name": appendix_info["appendix_name"],
                "rows": rows,
            })

        result.append({
            "statement": statement_meta,
            "plant": plant_meta,
            "appendices": appendices_block,
        })

    return result
