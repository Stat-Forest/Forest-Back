from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

from django.db import transaction
from django.db.models import Prefetch

from apps.utils.services import RegionChoices
from apps.utils.translation import get_translated_field
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn, Plant, Deadline

from apps.reports.services.get_calculation_for_generals import calculate_general_report
from apps.reports.services.report_calculate_expressions import calculate_by_expressions


# ============================================================
# Period parsing (agar ishlatsang)
# ============================================================

@dataclass
class PeriodRange:
    kind: str  # "year" | "quarter"
    year: int
    quarter: int | None = None


def parse_period(period: str) -> PeriodRange:
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
    return PeriodRange(kind="year", year=int(p))


# ============================================================
# Column rules
# ============================================================

def is_calculated_column(col) -> bool:
    """
    Aggregation paytida SUM qilinmasligi kerak bo'lgan ustunlar:
    - calculate_expression bor
    - is_user_input=False
    - title ichida % / foiz / percent / процент bor
    """
    if getattr(col, "calculate_expression", None):
        return True
    if getattr(col, "is_user_input", True) is False:
        return True

    titles = [
        getattr(col, "title", None),
        getattr(col, "title_uz", None),
        getattr(col, "title_ru", None),
    ]
    t = " ".join([x for x in titles if x]).lower()
    if ("%" in t) or ("foiz" in t) or ("percent" in t) or ("процент" in t):
        return True
    return False


def is_aggregatable_column(col) -> bool:
    return not is_calculated_column(col)


def _is_org_name_column(col: StatementColumn) -> bool:
    """
    Org-name ustuni (Tuman/Tashkilot nomi) bo'lib qolgan ustunlarni text sifatida qo'yib beramiz.
    """
    # flag bilan belgilangan bo'lsa ham ko'p hollarda shu chiqadi
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
        "нaименование организации".lower(),
        "название организации",
    ]
    return any(any(k in t for k in keys) for t in titles)


# ============================================================
# Helpers
# ============================================================

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
        .only(
            "id", "parent_id", "ordering",
            "title_uz", "title_ru",
            "is_organization", "is_user_input",
        )
    )
    by_id = {str(c.id): c for c in cols}
    by_parent: Dict[str | None, List[StatementColumn]] = defaultdict(list)
    for c in cols:
        by_parent[str(c.parent_id) if c.parent_id else None].append(c)

    # ordering sort
    def _ord_key(c: StatementColumn):
        parts = (c.ordering or "").split(".")
        out = []
        for p in parts:
            if p.isdigit():
                out.append(int(p))
            else:
                out.append(p)
        return out

    for k in by_parent:
        by_parent[k].sort(key=_ord_key)

    return by_id, by_parent


def _full_column_path(col: StatementColumn, by_id: Dict[str, StatementColumn], lang: str) -> str:
    parts: List[str] = []
    cur = col
    while cur is not None:
        title = get_translated_field(cur, "title", lang) or ""
        parts.append(title)
        pid = getattr(cur, "parent_id", None)
        cur = by_id.get(str(pid)) if pid else None
    parts.reverse()
    return " – ".join([p for p in parts if p])


def _prefetch_items_qs():
    return Prefetch(
        "report_items",
        queryset=(
            ReportItem.objects
            .select_related("statement_column", "statement_column__parent")
            .prefetch_related("inners", "inners__plant")
        ),
    )


# ============================================================
# Source: ACCEPTED individual reports for EXACT deadline
# ============================================================

def filter_reports_by_deadline(statement, deadline_id: str):
    """
    EXACT deadline bo'yicha ACCEPTED individual reportlar.
    (filtered-general endpoint ma'nosi shu bo'lsa)
    """
    qs = (
        Report.objects.filter(
            statement=statement,
            deadline_id=deadline_id,
            is_report=True,
            status=Report.StatusChoices.ACCEPTED,
            is_general=False,
            is_individual_general=False,
            is_republic=False,
        )
        .select_related("organization", "statement", "deadline")
        .prefetch_related(_prefetch_items_qs())
        .order_by("organization__name")
    )
    return qs


# ============================================================
# Create/Update DB GENERAL & REPUBLIC for this deadline
# ============================================================

def _sum_reports_for_general(reports: List[Report], by_id: Dict[str, StatementColumn]):
    """
    returns:
      totals[cid][plant_id_or_None] = Decimal
    Only aggregatable numeric columns are summed.
    """
    totals: Dict[str, Dict[str | None, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

    for rep in reports:
        for it in rep.report_items.all():
            cid = str(it.statement_column_id)
            col = by_id.get(cid)
            if not col:
                continue
            if _is_org_name_column(col):
                continue
            if not is_aggregatable_column(col):
                continue

            for inn in it.inners.all():
                plant_key = str(inn.plant_id) if getattr(inn, "plant_id", None) else None
                totals[cid][plant_key] += _safe_decimal(inn.value)

    return totals


def _ensure_general_report(statement, deadline_id: str, region_key: str) -> Optional[Report]:
    """
    DB’da (statement, deadline_id, region, is_general=True) general reportni bitta qilib yuritadi.
    """
    deadline = Deadline.objects.filter(id=deadline_id).first()
    if not deadline:
        return None

    qs = Report.objects.filter(
        statement=statement,
        deadline_id=deadline_id,
        region=region_key,
        is_general=True,
        organization__isnull=True,
    ).order_by("-created_at")

    general = qs.first()
    if qs.count() > 1 and general:
        qs.exclude(id=general.id).delete()

    if not general:
        general = Report.objects.create(
            organization=None,
            statement=statement,
            deadline=deadline,
            region=region_key,
            is_general=True,
            is_republic=False,
            is_individual_general=False,
            is_report=False,
            status=Report.StatusChoices.SAVED,
        )
    else:
        # flaglarni kafolatlaymiz
        updates = {}
        if general.is_report:
            updates["is_report"] = False
        if general.status != Report.StatusChoices.SAVED:
            updates["status"] = Report.StatusChoices.SAVED
        if general.deadline_id != deadline_id:
            updates["deadline_id"] = deadline_id
        if updates:
            for k, v in updates.items():
                setattr(general, k, v)
            general.save(update_fields=list(updates.keys()))

    return general


def _ensure_republic_report(statement, deadline_id: str) -> Optional[Report]:
    deadline = Deadline.objects.filter(id=deadline_id).first()
    if not deadline:
        return None

    qs = Report.objects.filter(
        statement=statement,
        deadline_id=deadline_id,
        is_republic=True,
        organization__isnull=True,
    ).order_by("-created_at")

    rep = qs.first()
    if qs.count() > 1 and rep:
        qs.exclude(id=rep.id).delete()

    if not rep:
        rep = Report.objects.create(
            organization=None,
            statement=statement,
            deadline=deadline,
            region=RegionChoices.REPUBLIC if hasattr(RegionChoices, "REPUBLIC") else None,
            is_republic=True,
            is_general=False,
            is_individual_general=False,
            is_report=False,
            status=Report.StatusChoices.SAVED,
        )
    else:
        updates = {}
        if rep.is_report:
            updates["is_report"] = False
        if rep.status != Report.StatusChoices.SAVED:
            updates["status"] = Report.StatusChoices.SAVED
        if rep.deadline_id != deadline_id:
            updates["deadline_id"] = deadline_id
        if updates:
            for k, v in updates.items():
                setattr(rep, k, v)
            rep.save(update_fields=list(updates.keys()))

    return rep


@transaction.atomic
def rebuild_general_for_deadline(statement, deadline_id: str, region_key: str, region_reports: List[Report]) -> Optional[Report]:
    """
    Region ACCEPTED reportlarini EXACT deadline bo'yicha yig'ib,
    DB general reportga yozadi va kalkulyatorni ishlatadi.
    """
    general = _ensure_general_report(statement, deadline_id, region_key)
    if not general:
        return None

    # eski item/innerlarni tozalash
    ReportItem.objects.filter(report=general).delete()

    by_id, _ = _build_statement_maps(statement)
    totals = _sum_reports_for_general(region_reports, by_id)

    # plant map (agar plant bo'lsa)
    plant_ids = {pid for per_plant in totals.values() for pid in per_plant.keys() if pid}
    plant_map = {str(pid): name for pid, name in Plant.objects.filter(id__in=plant_ids).values_list("id", "name")}

    # org-name columns: bitta item qilib text qo'yamiz
    org_name_cols = [c for c in by_id.values() if _is_org_name_column(c)]

    created_items: List[ReportItem] = []
    created_inners: List[ReportItemInner] = []

    # 1) org-name
    region_label = dict(RegionChoices.choices).get(str(region_key), str(region_key))
    for col in org_name_cols:
        item = ReportItem.objects.create(report=general, statement_column_id=col.id)
        created_items.append(item)
        created_inners.append(ReportItemInner(report_item=item, value=f"{region_label} – Viloyat Jami"))

    # 2) numeric totals
    for cid, per_plant in totals.items():
        item = ReportItem.objects.create(report=general, statement_column_id=cid)
        created_items.append(item)

        # stable: plants by name, then None
        plant_keys_sorted = sorted([k for k in per_plant.keys() if k], key=lambda k: plant_map.get(k, ""))
        for pk in plant_keys_sorted:
            created_inners.append(ReportItemInner(report_item=item, plant_id=pk, value=str(per_plant[pk])))
        if None in per_plant:
            created_inners.append(ReportItemInner(report_item=item, value=str(per_plant[None])))

    if created_inners:
        ReportItemInner.objects.bulk_create(created_inners)

    # kalkulyatorlar (% va boshqa computed lar)
    try:
        calculate_general_report(general)
    except Exception as e:
        # log qilsa bo'ladi
        print(f"[FILTERED][GENERAL] calculate_general_report error: {e}")

    try:
        if getattr(general.statement, "calculate_expression", None):
            calculate_by_expressions(general)
    except Exception as e:
        print(f"[FILTERED][GENERAL] calculate_by_expressions error: {e}")

    # qayta prefetch bilan qaytaramiz
    general = (
        Report.objects.filter(id=general.id)
        .select_related("statement", "deadline")
        .prefetch_related(_prefetch_items_qs())
        .first()
    )
    return general


@transaction.atomic
def rebuild_republic_for_deadline(statement, deadline_id: str, general_reports: List[Report]) -> Optional[Report]:
    """
    Shu deadline_id bo'yicha barcha viloyat general reportlardan Respublika jamini yasaydi.
    """
    rep = _ensure_republic_report(statement, deadline_id)
    if not rep:
        return None

    ReportItem.objects.filter(report=rep).delete()

    by_id, _ = _build_statement_maps(statement)

    # general reportlar ichidagi itemlardan SUM
    totals: Dict[str, Dict[str | None, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

    for gr in general_reports:
        for it in gr.report_items.all():
            cid = str(it.statement_column_id)
            col = by_id.get(cid)
            if not col:
                continue
            if _is_org_name_column(col):
                continue
            if not is_aggregatable_column(col):
                continue

            for inn in it.inners.all():
                plant_key = str(inn.plant_id) if getattr(inn, "plant_id", None) else None
                totals[cid][plant_key] += _safe_decimal(inn.value)

    plant_ids = {pid for per_plant in totals.values() for pid in per_plant.keys() if pid}
    plant_map = {str(pid): name for pid, name in Plant.objects.filter(id__in=plant_ids).values_list("id", "name")}

    org_name_cols = [c for c in by_id.values() if _is_org_name_column(c)]

    created_inners: List[ReportItemInner] = []

    # org-name
    for col in org_name_cols:
        item = ReportItem.objects.create(report=rep, statement_column_id=col.id)
        created_inners.append(ReportItemInner(report_item=item, value="Respublika Jami"))

    # numeric totals
    for cid, per_plant in totals.items():
        item = ReportItem.objects.create(report=rep, statement_column_id=cid)

        plant_keys_sorted = sorted([k for k in per_plant.keys() if k], key=lambda k: plant_map.get(k, ""))
        for pk in plant_keys_sorted:
            created_inners.append(ReportItemInner(report_item=item, plant_id=pk, value=str(per_plant[pk])))
        if None in per_plant:
            created_inners.append(ReportItemInner(report_item=item, value=str(per_plant[None])))

    if created_inners:
        ReportItemInner.objects.bulk_create(created_inners)

    try:
        calculate_general_report(rep)
    except Exception as e:
        print(f"[FILTERED][REPUBLIC] calculate_general_report error: {e}")

    try:
        if getattr(rep.statement, "calculate_expression", None):
            calculate_by_expressions(rep)
    except Exception as e:
        print(f"[FILTERED][REPUBLIC] calculate_by_expressions error: {e}")

    rep = (
        Report.objects.filter(id=rep.id)
        .select_related("statement", "deadline")
        .prefetch_related(_prefetch_items_qs())
        .first()
    )
    return rep


# ============================================================
# Serialization helpers (ReportListSerializer-like)
# ============================================================

def _serialize_report_like(rep: Report, by_id: Dict[str, StatementColumn], lang: str, org_name_override: Optional[str] = None) -> Dict:
    org_name = org_name_override
    if org_name is None:
        if getattr(rep, "organization", None):
            org_name = get_translated_field(rep.organization, "name", lang) or ""
        else:
            org_name = rep.organization_name if hasattr(rep, "organization_name") else ""

    # plant names map (for stable ordering)
    plant_ids_all: set[str] = set()
    for it in rep.report_items.all():
        for inn in it.inners.all():
            if getattr(inn, "plant_id", None):
                plant_ids_all.add(str(inn.plant_id))
    plant_map_all = {str(pid): name for pid, name in Plant.objects.filter(id__in=plant_ids_all).values_list("id", "name")}

    statement_columns_payload = []
    for it in rep.report_items.all():
        col = getattr(it, "statement_column", None) or by_id.get(str(it.statement_column_id))
        if not col:
            continue

        cid = str(it.statement_column_id)
        inners_payload = []

        # stable: plants by name then None
        inners = list(it.inners.all())
        def _inner_key(x):
            pid = getattr(x, "plant_id", None)
            if pid:
                return (0, plant_map_all.get(str(pid), ""))
            return (1, "")
        inners.sort(key=_inner_key)

        for inn in inners:
            payload = {"value": inn.value}
            if getattr(inn, "plant_id", None):
                payload["plant_id"] = str(inn.plant_id)
                payload["plant_name"] = plant_map_all.get(str(inn.plant_id), "")
            inners_payload.append(payload)

        statement_columns_payload.append({
            "statement_column_id": cid,
            "statement_column_name": _full_column_path(col, by_id, lang),
            "inners": inners_payload,
        })

    return {
        "id": str(rep.id),
        "organization": str(getattr(rep.organization, "id", "")) if getattr(rep, "organization", None) else None,
        "organization_name": org_name,
        "statement": str(rep.statement_id),
        "deadline": str(rep.deadline_id) if getattr(rep, "deadline_id", None) else None,
        "report_items": [
            {
                "organization_id": str(getattr(rep.organization, "id", "")) if getattr(rep, "organization", None) else None,
                "organization_name": org_name,
                "statement_columns": statement_columns_payload,
            }
        ],
        "is_general": bool(getattr(rep, "is_general", False)),
        "is_individual_general": bool(getattr(rep, "is_individual_general", False)),
        "is_republic": bool(getattr(rep, "is_republic", False)),
    }


# ============================================================
# Main payload builder
# ============================================================

def build_filtered_payload(statement, deadline_id: str, lang: str) -> Dict:
    """
    ✅ FIXED:
    - Region/Repub hisoblash endi snapshot emas, DB report orqali qilinadi.
    - Har bir region uchun general report shu deadline_id bilan rebuild qilinadi.
    - Republic ham shu deadline_id bilan rebuild qilinadi.
    - Keyin DB reportlar serialize qilinib qaytariladi.
    """

    # 1) individual accepted reports exact deadline
    individuals = list(filter_reports_by_deadline(statement, deadline_id))

    # 2) group by region
    by_region: Dict[str, List[Report]] = defaultdict(list)
    for rep in individuals:
        region_key = str(getattr(rep.organization, "region", ""))
        by_region[region_key].append(rep)

    # 3) statement column map for paths
    by_id, _ = _build_statement_maps(statement)

    results = []

    # 4) rebuild each region general and serialize
    region_general_reports: List[Report] = []

    for region_key, reps in by_region.items():
        # (A) rebuild DB general for this deadline+region from these reps
        general_rep = rebuild_general_for_deadline(statement, deadline_id, region_key, reps)
        if general_rep:
            region_general_reports.append(general_rep)

        # (B) children: individuals serialize (unchanged)
        children_payload = [
            {
                "id": _serialize_report_like(r, by_id, lang)["id"],
                "organization_name": _serialize_report_like(r, by_id, lang)["organization_name"],
                "report_items": _serialize_report_like(r, by_id, lang)["report_items"],
                "sent_by_full_name": None,
                "sent_by_org_name": _serialize_report_like(r, by_id, lang)["organization_name"],
                "sent_by_role": None,
            }
            for r in reps
        ]

        # (C) region item (parent)
        if general_rep:
            parent_payload = _serialize_report_like(general_rep, by_id, lang, org_name_override=f"{region_key} – Viloyat Jami")
            results.append({
                "id": parent_payload["id"],
                "organization_name": parent_payload["organization_name"] or f"{region_key} – Viloyat Jami",
                "report_items": parent_payload["report_items"],
                "children_reports": children_payload,
            })
        else:
            # general yo'q bo'lsa ham region blokni bo'sh qaytarish
            results.append({
                "id": None,
                "organization_name": f"{region_key} – Viloyat Jami",
                "report_items": [{"organization_id": "general", "organization_name": f"{region_key} – Viloyat Jami", "statement_columns": []}],
                "children_reports": children_payload,
            })

    # 5) rebuild republic from region generals (this deadline)
    republic_rep = rebuild_republic_for_deadline(statement, deadline_id, region_general_reports)
    if republic_rep:
        rep_payload = _serialize_report_like(republic_rep, by_id, lang, org_name_override="Respublika Jami")
        results.append({
            "id": rep_payload["id"],
            "organization_name": rep_payload["organization_name"] or "Respublika Jami",
            "report_items": rep_payload["report_items"],
            "children_reports": [],
        })
    else:
        results.append({
            "id": None,
            "organization_name": "Respublika Jami",
            "report_items": [{"organization_id": "republic", "organization_name": "Respublika Jami", "statement_columns": []}],
            "children_reports": [],
        })

    return {
        "count": len(results),
        "next": None,
        "previous": None,
        "results": results,
    }
