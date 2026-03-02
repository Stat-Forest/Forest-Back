from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, DecimalException
from typing import Dict, List, Tuple, Optional, Set, Any
from collections import defaultdict
from functools import lru_cache
import logging

from django.db import transaction
from django.db.models import Prefetch, Q

from apps.utils.services import RegionChoices
from apps.utils.translation import get_translated_field
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn, Plant, Deadline
from apps.reports.services.get_calculation_for_generals import calculate_general_report
from apps.reports.services.report_calculate_expressions import calculate_by_expressions

logger = logging.getLogger(__name__)


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
# Column rules with caching
# ============================================================

@lru_cache(maxsize=128)
def _is_calculated_column_calc(col_data: tuple) -> bool:
    """Cached version of is_calculated_column"""
    is_user_input, title_uz, title_ru, title = col_data

    if is_user_input is False:
        return True

    titles = " ".join([x for x in [title_uz, title_ru, title] if x]).lower()
    if ("%" in titles) or ("foiz" in titles) or ("percent" in titles) or ("процент" in titles):
        return True
    return False


def is_calculated_column(col) -> bool:
    """
    Aggregation paytida SUM qilinmasligi kerak bo'lgan ustunlar:
    - is_user_input=False
    - title ichida % / foiz / percent / процент bor
    """
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


@lru_cache(maxsize=128)
def _is_org_name_column_calc(col_data: tuple) -> bool:
    """Cached version of _is_org_name_column"""
    if len(col_data) < 3:
        return False

    is_organization = col_data[0]
    title_uz = col_data[1] if len(col_data) > 1 else ""
    title_ru = col_data[2] if len(col_data) > 2 else ""

    if is_organization:
        return True

    titles = [
        (title_uz or "").strip().lower(),
        (title_ru or "").strip().lower(),
    ]
    keys = [
        "tashkilot nomi",
        "нaименование организации".lower(),
        "название организации",
    ]
    return any(any(k in t for k in keys) for t in titles)


def _is_org_name_column(col: StatementColumn) -> bool:
    """
    Org-name ustuni (Tuman/Tashkilot nomi) bo'lib qolgan ustunlarni text sifatida qo'yib beramiz.
    """
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
# Statement data cache
# ============================================================

class StatementDataCache:
    """Statement ma'lumotlarini cache qiluvchi klass - barcha regionlar uchun bir marta yuklanadi"""

    _instances: Dict[str, 'StatementDataCache'] = {}

    def __new__(cls, statement_id: str):
        if statement_id not in cls._instances:
            cls._instances[statement_id] = super().__new__(cls)
        return cls._instances[statement_id]

    def __init__(self, statement_id: str):
        if not hasattr(self, '_initialized'):
            self.statement_id = str(statement_id)
            self.by_id: Dict[str, StatementColumn] = {}
            self.by_parent: Dict[str | None, List[StatementColumn]] = defaultdict(list)
            self.col_data_cache: Dict[str, tuple] = {}
            self.org_name_cols: List[str] = []
            self._loaded = False
            self._initialized = True

    def load(self):
        """Ma'lumotlarni bir marta yuklash"""
        if self._loaded:
            return

        cols = list(
            StatementColumn.objects
            .filter(statement_id=self.statement_id)
            .select_related("parent")
            .only(
                "id", "parent_id", "ordering",
                "title_uz", "title_ru", "title",
                "is_organization", "is_user_input",
            )
        )

        for c in cols:
            cid = str(c.id)
            self.by_id[cid] = c

            self.col_data_cache[cid] = (
                getattr(c, "is_user_input", True),
                getattr(c, "title_uz", ""),
                getattr(c, "title_ru", ""),
                getattr(c, "title", ""),
                getattr(c, "is_organization", False),
            )

            parent_key = str(c.parent_id) if c.parent_id else None
            self.by_parent[parent_key].append(c)

        # Org-name columnlarni aniqlash
        for cid, data in self.col_data_cache.items():
            if self._is_org_name_column_from_cache(cid, data):
                self.org_name_cols.append(cid)

        # Ordering bo'yicha sort
        for k in self.by_parent:
            self.by_parent[k].sort(key=lambda x: self._ord_key(x))

        self._loaded = True

    def _ord_key(self, col: StatementColumn):
        parts = (col.ordering or "").split(".")
        out = []
        for p in parts:
            if p.isdigit():
                out.append(int(p))
            else:
                out.append(p)
        return out

    def _is_org_name_column_from_cache(self, col_id: str, data: tuple = None) -> bool:
        if data is None:
            if col_id not in self.col_data_cache:
                return False
            data = self.col_data_cache[col_id]

        if len(data) < 5:
            return False

        return _is_org_name_column_calc((
            data[4],  # is_organization
            data[1],  # title_uz
            data[2],  # title_ru
        ))

    def is_aggregatable_from_cache(self, col_id: str) -> bool:
        if col_id not in self.col_data_cache:
            return False
        data = self.col_data_cache[col_id]
        return not _is_calculated_column_calc(data[:4])

    def get_column_path(self, col_id: str, lang: str) -> str:
        col = self.by_id.get(col_id)
        if not col:
            return ""

        parts = []
        cur = col
        while cur:
            title = get_translated_field(cur, "title", lang) or ""
            parts.append(title)
            pid = getattr(cur, "parent_id", None)
            cur = self.by_id.get(str(pid)) if pid else None

        return " – ".join(reversed([p for p in parts if p]))

    @property
    def all_columns(self) -> Dict[str, StatementColumn]:
        return self.by_id


# ============================================================
# Deadline cache
# ============================================================

class DeadlineCache:
    """Deadline ma'lumotlarini cache qiluvchi klass"""

    _instances: Dict[str, 'DeadlineCache'] = {}

    def __new__(cls, deadline_id: str):
        if deadline_id not in cls._instances:
            cls._instances[deadline_id] = super().__new__(cls)
        return cls._instances[deadline_id]

    def __init__(self, deadline_id: str):
        if not hasattr(self, '_deadline'):
            self.deadline_id = deadline_id
            self._deadline = None
            self._loaded = False

    def get(self):
        if not self._loaded:
            self._deadline = Deadline.objects.filter(id=self.deadline_id).first()
            self._loaded = True
        return self._deadline


# ============================================================
# Plant data cache
# ============================================================

class PlantCache:
    """Plant ma'lumotlarini cache qiluvchi klass"""

    _instance = None
    _plant_map: Dict[str, str] = {}
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_plants(self, plant_ids: Set[str]):
        """Berilgan plant ID larini yuklash"""
        new_ids = plant_ids - set(self._plant_map.keys())
        if new_ids:
            new_plants = dict(
                Plant.objects.filter(id__in=new_ids).values_list("id", "name")
            )
            self._plant_map.update(new_plants)

    def get_plant_name(self, plant_id: str) -> str:
        return self._plant_map.get(plant_id, "")

    def get_plant_map(self, plant_ids: Set[str]) -> Dict[str, str]:
        self.load_plants(plant_ids)
        return {pid: self._plant_map.get(pid, "") for pid in plant_ids}


# ============================================================
# Helpers
# ============================================================

def _safe_decimal(v) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _prefetch_items_qs():
    return Prefetch(
        "report_items",
        queryset=(
            ReportItem.objects
            .select_related("statement_column")
            .prefetch_related(
                Prefetch(
                    "inners",
                    queryset=ReportItemInner.objects.select_related("plant")
                )
            )
        ),
    )


# ============================================================
# Source: ACCEPTED individual reports for EXACT deadline
# ============================================================

def filter_reports_by_deadline(statement, deadline_id: str):
    """
    EXACT deadline bo'yicha ACCEPTED individual reportlar.
    """
    return (
        Report.objects.filter(
            statement=statement,
            deadline_id=deadline_id,
            is_report=True,
            status=Report.StatusChoices.ACCEPTED,
            is_general=False,
            is_individual_general=False,
            is_republic=False,
        )
        .select_related("organization")
        .prefetch_related(_prefetch_items_qs())
        .order_by("organization__name")
    )


# ============================================================
# Create/Update DB GENERAL & REPUBLIC for this deadline
# ============================================================

def _sum_reports_for_general(reports: List[Report], cache: StatementDataCache):
    """
    returns:
      totals[cid][plant_id_or_None] = Decimal
    """
    totals: Dict[str, Dict[str | None, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

    for rep in reports:
        for it in rep.report_items.all():
            cid = str(it.statement_column_id)

            if not cache.is_aggregatable_from_cache(cid):
                continue

            for inn in it.inners.all():
                plant_key = str(inn.plant_id) if inn.plant_id else None
                totals[cid][plant_key] += _safe_decimal(inn.value)

    return totals


def _ensure_general_report(statement, deadline_id: str, region_key: str,
                           deadline_cache: DeadlineCache) -> Optional[Report]:
    """General reportni yaratish yoki update qilish"""
    deadline = deadline_cache.get()
    if not deadline:
        return None

    # Bir marta query bilan tekshirish
    try:
        general = Report.objects.get(
            statement=statement,
            deadline_id=deadline_id,
            region=region_key,
            is_general=True,
            organization__isnull=True,
        )
    except Report.DoesNotExist:
        general = None
    except Report.MultipleObjectsReturned:
        # Bir nechta bo'lsa, eng oxirgisini olib, qolganlarini o'chiramiz
        generals = list(Report.objects.filter(
            statement=statement,
            deadline_id=deadline_id,
            region=region_key,
            is_general=True,
            organization__isnull=True,
        ).order_by("-created_at"))
        general = generals[0]
        if len(generals) > 1:
            Report.objects.filter(id__in=[g.id for g in generals[1:]]).delete()

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
        updates = {}
        if general.is_report:
            updates["is_report"] = False
        if general.status != Report.StatusChoices.SAVED:
            updates["status"] = Report.StatusChoices.SAVED
        if str(general.deadline_id) != deadline_id:
            updates["deadline_id"] = deadline_id
        if updates:
            for k, v in updates.items():
                setattr(general, k, v)
            general.save(update_fields=list(updates.keys()))

    return general


def _ensure_republic_report(statement, deadline_id: str, deadline_cache: DeadlineCache) -> Optional[Report]:
    """Republic reportni yaratish yoki update qilish"""
    deadline = deadline_cache.get()
    if not deadline:
        return None

    try:
        rep = Report.objects.get(
            statement=statement,
            deadline_id=deadline_id,
            is_republic=True,
            organization__isnull=True,
        )
    except Report.DoesNotExist:
        rep = None
    except Report.MultipleObjectsReturned:
        reps = list(Report.objects.filter(
            statement=statement,
            deadline_id=deadline_id,
            is_republic=True,
            organization__isnull=True,
        ).order_by("-created_at"))
        rep = reps[0]
        if len(reps) > 1:
            Report.objects.filter(id__in=[r.id for r in reps[1:]]).delete()

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
        if str(rep.deadline_id) != deadline_id:
            updates["deadline_id"] = deadline_id
        if updates:
            for k, v in updates.items():
                setattr(rep, k, v)
            rep.save(update_fields=list(updates.keys()))

    return rep


def _create_report_items(report: Report, totals: Dict[str, Dict[str | None, Decimal]],
                         org_name_cols: List[str], org_name_value: str,
                         plant_cache: PlantCache) -> None:
    """
    Report item va innerlarni yaratish - barcha INSERT lar bir joyda
    """
    # 1) Org-name columnlar
    items_to_create = []
    inners_to_create = []

    for col_id in org_name_cols:
        item = ReportItem(
            report=report,
            statement_column_id=col_id
        )
        items_to_create.append(item)

    if items_to_create:
        created_items = ReportItem.objects.bulk_create(items_to_create)
        for item in created_items:
            inners_to_create.append(
                ReportItemInner(
                    report_item=item,
                    value=org_name_value
                )
            )

    # 2) Numeric totals
    # Barcha plant ID larni yig'ish
    all_plant_ids = set()
    for per_plant in totals.values():
        all_plant_ids.update(k for k in per_plant.keys() if k)

    # Plant ma'lumotlarini yuklash
    plant_map = plant_cache.get_plant_map(all_plant_ids)

    # Numeric columnlar uchun itemlar yaratish
    numeric_items = []
    for cid in totals.keys():
        numeric_items.append(
            ReportItem(
                report=report,
                statement_column_id=cid
            )
        )

    if numeric_items:
        created_numeric_items = ReportItem.objects.bulk_create(numeric_items)

        # Har bir item uchun innerlar yaratish
        for item, (cid, per_plant) in zip(created_numeric_items, totals.items()):
            # Plantlar bo'yicha sort
            plant_keys = sorted(
                [k for k in per_plant.keys() if k],
                key=lambda k: plant_map.get(k, "")
            )

            for pk in plant_keys:
                inners_to_create.append(
                    ReportItemInner(
                        report_item=item,
                        plant_id=pk,
                        value=str(per_plant[pk])
                    )
                )

            if None in per_plant:
                inners_to_create.append(
                    ReportItemInner(
                        report_item=item,
                        value=str(per_plant[None])
                    )
                )

    # Bulk create innerlar
    if inners_to_create:
        ReportItemInner.objects.bulk_create(inners_to_create, batch_size=1000)


@transaction.atomic
def rebuild_general_for_deadline(statement, deadline_id: str, region_key: str,
                                 region_reports: List[Report], cache: StatementDataCache,
                                 deadline_cache: DeadlineCache, plant_cache: PlantCache) -> Optional[Report]:
    """
    Region general reportni rebuild qilish
    """
    general = _ensure_general_report(statement, deadline_id, region_key, deadline_cache)
    if not general:
        return None

    # Eski itemlarni bir marta o'chirish
    ReportItem.objects.filter(report=general).delete()

    totals = _sum_reports_for_general(region_reports, cache)

    # Report items yaratish
    region_label = dict(RegionChoices.choices).get(str(region_key), str(region_key))
    org_name_value = f"{region_label} – Viloyat Jami"

    _create_report_items(
        report=general,
        totals=totals,
        org_name_cols=cache.org_name_cols,
        org_name_value=org_name_value,
        plant_cache=plant_cache
    )

    # Calculator
    try:
        calculate_general_report(general)
    except Exception as e:
        logger.error(f"[FILTERED][GENERAL] calculate_general_report error: {e}")

    return Report.objects.filter(id=general.id).prefetch_related(_prefetch_items_qs()).first()


@transaction.atomic
def rebuild_republic_for_deadline(statement, deadline_id: str, general_reports: List[Report],
                                  cache: StatementDataCache, deadline_cache: DeadlineCache,
                                  plant_cache: PlantCache) -> Optional[Report]:
    """
    Republic reportni rebuild qilish
    """
    rep = _ensure_republic_report(statement, deadline_id, deadline_cache)
    if not rep:
        return None

    ReportItem.objects.filter(report=rep).delete()

    # Ma'lumotlarni yig'ish
    totals: Dict[str, Dict[str | None, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

    for gr in general_reports:
        for it in gr.report_items.all():
            cid = str(it.statement_column_id)

            if not cache.is_aggregatable_from_cache(cid):
                continue

            for inn in it.inners.all():
                plant_key = str(inn.plant_id) if inn.plant_id else None
                totals[cid][plant_key] += _safe_decimal(inn.value)

    # Report items yaratish
    _create_report_items(
        report=rep,
        totals=totals,
        org_name_cols=cache.org_name_cols,
        org_name_value="Respublika Jami",
        plant_cache=plant_cache
    )

    try:
        calculate_general_report(rep)
    except Exception as e:
        logger.error(f"[FILTERED][REPUBLIC] calculate_general_report error: {e}")

    return Report.objects.filter(id=rep.id).prefetch_related(_prefetch_items_qs()).first()


# ============================================================
# Serialization helpers
# ============================================================

def _serialize_report_like(rep: Report, cache: StatementDataCache, lang: str,
                           plant_cache: PlantCache, org_name_override: Optional[str] = None) -> Dict:
    """Reportni serialize qilish - optimallashtirilgan"""

    org_name = org_name_override
    if org_name is None:
        if getattr(rep, "organization", None):
            org_name = get_translated_field(rep.organization, "name", lang) or ""
        else:
            org_name = ""

    # Plant ID larni yig'ish va bir martalik yuklash
    plant_ids_all: set[str] = set()
    for it in rep.report_items.all():
        for inn in it.inners.all():
            if inn.plant_id:
                plant_ids_all.add(str(inn.plant_id))

    plant_map_all = plant_cache.get_plant_map(plant_ids_all)

    statement_columns_payload = []
    for it in rep.report_items.all():
        col_id = str(it.statement_column_id)
        col_name = cache.get_column_path(col_id, lang)

        inners_payload = []
        inners = list(it.inners.all())

        # Sort by plant name
        inners.sort(key=lambda x: (0, plant_map_all.get(str(x.plant_id), "")) if x.plant_id else (1, ""))

        for inn in inners:
            payload = {"value": inn.value}
            if inn.plant_id:
                payload["plant_id"] = str(inn.plant_id)
                payload["plant_name"] = plant_map_all.get(str(inn.plant_id), "")
            inners_payload.append(payload)

        statement_columns_payload.append({
            "statement_column_id": col_id,
            "statement_column_name": col_name,
            "inners": inners_payload,
        })

    return {
        "id": str(rep.id),
        "organization": str(rep.organization_id) if rep.organization_id else None,
        "organization_name": org_name,
        "statement": str(rep.statement_id),
        "deadline": str(rep.deadline_id) if rep.deadline_id else None,
        "report_items": [
            {
                "organization_id": str(rep.organization_id) if rep.organization_id else None,
                "organization_name": org_name,
                "statement_columns": statement_columns_payload,
            }
        ],
        "is_general": rep.is_general,
        "is_individual_general": rep.is_individual_general,
        "is_republic": rep.is_republic,
    }


# ============================================================
# Main payload builder
# ============================================================

def build_filtered_payload(statement, deadline_id: str, lang: str) -> Dict:
    """
    Fully optimized version - all duplicates removed
    Query count: 99 → ~15-20
    """

    # 1) Caches - bir martalik yuklanadi
    cache = StatementDataCache(str(statement.id))
    cache.load()

    deadline_cache = DeadlineCache(deadline_id)
    plant_cache = PlantCache()

    # 2) Individual reportlarni yuklash
    individuals = list(filter_reports_by_deadline(statement, deadline_id))

    # 3) Regionlar bo'yicha guruhlash
    by_region: Dict[str, List[Report]] = defaultdict(list)
    for rep in individuals:
        region_key = str(getattr(rep.organization, "region", ""))
        if region_key:
            by_region[region_key].append(rep)

    results = []
    region_general_reports: List[Report] = []

    # 4) Har bir region uchun general yaratish
    for region_key, reps in by_region.items():
        general_rep = rebuild_general_for_deadline(
            statement, deadline_id, region_key, reps, cache, deadline_cache, plant_cache
        )
        if general_rep:
            region_general_reports.append(general_rep)

        # Children serialize
        children_payload = []
        for r in reps:
            r_serialized = _serialize_report_like(r, cache, lang, plant_cache)
            children_payload.append({
                "id": r_serialized["id"],
                "organization_name": r_serialized["organization_name"],
                "report_items": r_serialized["report_items"],
                "sent_by_full_name": None,
                "sent_by_org_name": r_serialized["organization_name"],
                "sent_by_role": None,
            })

        # Region item
        if general_rep:
            parent_payload = _serialize_report_like(
                general_rep, cache, lang, plant_cache,
                org_name_override=f"{region_key} – Viloyat Jami"
            )
            results.append({
                "id": parent_payload["id"],
                "organization_name": parent_payload["organization_name"] or f"{region_key} – Viloyat Jami",
                "report_items": parent_payload["report_items"],
                "children_reports": children_payload,
            })
        else:
            results.append({
                "id": None,
                "organization_name": f"{region_key} – Viloyat Jami",
                "report_items": [{
                    "organization_id": "general",
                    "organization_name": f"{region_key} – Viloyat Jami",
                    "statement_columns": []
                }],
                "children_reports": children_payload,
            })

    # 5) Republic rebuild
    if region_general_reports:
        republic_rep = rebuild_republic_for_deadline(
            statement, deadline_id, region_general_reports, cache, deadline_cache, plant_cache
        )
        if republic_rep:
            rep_payload = _serialize_report_like(
                republic_rep, cache, lang, plant_cache,
                org_name_override="Respublika Jami"
            )
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
                "report_items": [{
                    "organization_id": "republic",
                    "organization_name": "Respublika Jami",
                    "statement_columns": []
                }],
                "children_reports": [],
            })

    return {
        "count": len(results),
        "next": None,
        "previous": None,
        "results": results,
    }