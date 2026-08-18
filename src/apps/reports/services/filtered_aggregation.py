from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Optional, Set

from django.db import transaction
from django.db.models import Prefetch, Q

from apps.utils.services import RegionChoices
from apps.utils.translation import get_translated_field
from apps.reports.services.get_calculation_for_generals import calculate_general_report
from apps.reports.services.report_calculate_expressions import calculate_by_expressions
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn, Plant, Deadline

logger = logging.getLogger(__name__)

# ============================================================
# Constants
# ============================================================

PLAN_FROM_INDIVIDUAL_GENERAL_STATEMENTS = {
    "Urug' xarakati Reja",
    "Og'ir mahalla",
}

DAROMAD_NAMES = {"Daromad"}

# Har bir quarter uchun barcha kiruvchi Amalda ordering'lar.
# Oylik Amalda (X.Y.2.Z.2) + chorak reja section Amalda (X.Y.1.2)
DAROMAD_QUARTER_AMALDA_ORDERINGS: dict[str, frozenset[str]] = {
    "q1": frozenset([
        "1.3.2.1.2",  # Yanvar   Amalda
        "1.3.2.2.2",  # Fevral   Amalda
        "1.3.2.3.2",  # Mart     Amalda
        "1.3.1.2",    # 1-chorak reja → Amalda
    ]),
    "q2": frozenset([
        "1.4.2.1.2",  # Aprel    Amalda
        "1.4.2.2.2",  # May      Amalda
        "1.4.2.3.2",  # Iyun     Amalda
        "1.4.1.2",    # 2-chorak reja → Amalda
    ]),
    "q3": frozenset([
        "1.5.2.1.2",  # Iyul     Amalda
        "1.5.2.2.2",  # Avgust   Amalda
        "1.5.2.3.2",  # Sentabr  Amalda
        "1.5.1.2",    # 3-chorak reja → Amalda
    ]),
    "q4": frozenset([
        "1.6.2.1.2",  # Oktabr   Amalda
        "1.6.2.2.2",  # Noyabr   Amalda
        "1.6.2.3.2",  # Dekabr   Amalda
        "1.6.1.2",    # 4-chorak reja → Amalda
    ]),
}

# Barcha ruxsat etilgan Amalda ordering'lar (quarter filtr uchun emas, tez lookup uchun)
_ALL_DAROMAD_AMALDA_ORDERINGS: frozenset[str] = frozenset(
    o for orderings in DAROMAD_QUARTER_AMALDA_ORDERINGS.values() for o in orderings
)


# ============================================================
# Daromad helpers
# ============================================================

def _is_daromad_statement(statement) -> bool:
    name_uz = (getattr(statement, "name_uz", "") or "").strip()
    name = (getattr(statement, "name", "") or "").strip()
    return name_uz in DAROMAD_NAMES or name in DAROMAD_NAMES


def _get_accepted_quarters(report: Report) -> list[str]:
    """
    Report'dan ACCEPTED bo'lgan quarter'lar ro'yxatini qaytaradi.
    Masalan: Q1=ACCEPTED, Q2=SAVED → ["q1"]
    """
    accepted = []
    for q in ("q1", "q2", "q3", "q4"):
        status = getattr(report, f"quarter_{q[-1]}_status", None)
        if status == Report.StatusChoices.ACCEPTED:
            accepted.append(q)
    return accepted


def should_use_individual_general_plan_source(statement) -> bool:
    statement_names = {
        (getattr(statement, "name", "") or "").strip(),
        (getattr(statement, "name_uz", "") or "").strip(),
    }
    return bool(statement_names & PLAN_FROM_INDIVIDUAL_GENERAL_STATEMENTS)


def _get_global_plan_reja_col_ids(statement, cache: StatementDataCache) -> Set[str]:
    """
    Global plan statementlar uchun Reja column IDlarini ordering bo'yicha aniqlaydi.
    Bu columnlar individual_general (Tashkilot Jami) reportlardan olinishi kerak.
    general_report.py dagi statement_has_global_plan logikasi bilan mos.
    """
    stmt_name = (getattr(statement, "name", "") or getattr(statement, "name_uz", "") or "").strip().lower()

    if any(k in stmt_name for k in ("urug", "seed")):
        reja_orderings = ["1.1.2.1"]
    elif any(k in stmt_name for k in ("og'ir", "ogir", "mahalla")):
        reja_orderings = ["1.1.4"]
    else:
        return set()

    result: Set[str] = set()
    for ordering in reja_orderings:
        col_id = cache.get_col_id_by_ordering(ordering)
        if col_id:
            result.add(col_id)
    return result


# ============================================================
# Column helpers — singleton YO'Q, har doim fresh hisoblaydi
# ============================================================

def _is_calculated_column(col: StatementColumn) -> bool:
    """
    Aggregation paytida SUM qilinmasligi kerak bo'lgan ustunlar.
    Singleton/lru_cache ishlatilmaydi — col Django model instance,
    hashable emas, lru_cache xato beradi.
    """
    # Reja columnlar — har doim aggregatable
    if getattr(col, "status_plan", None):
        return False

    if getattr(col, "calculate_expression", None):
        return True

    if getattr(col, "is_user_input", True) is False:
        return True

    titles = " ".join(filter(None, [
        getattr(col, "title", None),
        getattr(col, "title_uz", None),
        getattr(col, "title_ru", None),
    ])).lower()

    return "%" in titles or "foiz" in titles or "percent" in titles or "процент" in titles


def _is_org_name_column(col: StatementColumn) -> bool:
    if getattr(col, "is_organization", False):
        return True
    titles = [
        (getattr(col, "title_uz", "") or "").strip().lower(),
        (getattr(col, "title_ru", "") or "").strip().lower(),
    ]
    keys = ["tashkilot nomi", "наименование организации", "название организации"]
    return any(any(k in t for k in keys) for t in titles)


# ============================================================
# Request-scoped cache (singleton emas — har request uchun yangi)
# ============================================================

class StatementDataCache:
    """
    Statement column ma'lumotlarini bir request ichida cache qiladi.
    SINGLETON EMAS — build_filtered_payload ichida har safar yangi instance yaratiladi.
    Bu server restart siz ham cache stale bo'lmasligini kafolatlaydi.
    """

    def __init__(self, statement_id: str):
        self.statement_id = str(statement_id)
        # col_id (str) → StatementColumn
        self.by_id: Dict[str, StatementColumn] = {}
        # col_id → bool (aggregatable yoki yo'q)
        self._aggregatable_cache: Dict[str, bool] = {}
        # col_id → bool (plan column yoki yo'q)
        self._plan_cache: Dict[str, bool] = {}
        # org-name column id'lari
        self.org_name_cols: List[str] = []
        # Daromad: ordering → col_id (tez lookup uchun)
        self._ordering_to_col_id: Dict[str, str] = {}

    def load(self) -> None:
        cols = list(
            StatementColumn.objects
            .filter(statement_id=self.statement_id)
            .only(
                "id", "parent_id", "ordering",
                "title_uz", "title_ru", "title",
                "is_organization", "is_user_input",
                "status_plan",
            )
        )

        for c in cols:
            cid = str(c.id)
            self.by_id[cid] = c
            self._aggregatable_cache[cid] = not _is_calculated_column(c)
            self._plan_cache[cid] = bool(getattr(c, "status_plan", None))
            self._ordering_to_col_id[c.ordering or ""] = cid

            if _is_org_name_column(c):
                self.org_name_cols.append(cid)

    def is_aggregatable(self, col_id: str) -> bool:
        return self._aggregatable_cache.get(col_id, False)

    def is_plan_column(self, col_id: str) -> bool:
        return self._plan_cache.get(col_id, False)

    def get_col_id_by_ordering(self, ordering: str) -> Optional[str]:
        return self._ordering_to_col_id.get(ordering)

    def get_column_path(self, col_id: str, lang: str) -> str:
        col = self.by_id.get(col_id)
        if not col:
            return ""
        parts = []
        cur = col
        while cur:
            title = get_translated_field(cur, "title", lang) or ""
            if title:
                parts.append(title)
            pid = getattr(cur, "parent_id", None)
            cur = self.by_id.get(str(pid)) if pid else None
        return " – ".join(reversed(parts))

    def build_daromad_allowed_col_ids(self, accepted_quarters: list[str]) -> set[str]:
        """
        Faqat ACCEPTED quarter'larning Amalda column'larini + Reja + is_organization
        col_id set sifatida qaytaradi.
        """
        allowed_orderings: set[str] = set()
        for q in accepted_quarters:
            allowed_orderings.update(DAROMAD_QUARTER_AMALDA_ORDERINGS.get(q, frozenset()))

        result: set[str] = set()
        for col_id, col in self.by_id.items():
            if getattr(col, "is_organization", False):
                result.add(col_id)
                continue
            if getattr(col, "status_plan", None):
                result.add(col_id)
                continue
            if (col.ordering or "") in allowed_orderings:
                result.add(col_id)
        return result

    @property
    def all_columns(self) -> Dict[str, StatementColumn]:
        return self.by_id


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
                    queryset=ReportItemInner.objects.select_related("plant"),
                )
            )
        ),
    )


# ============================================================
# Query helpers
# ============================================================

def filter_reports_by_deadline(statement, deadline_id: str, quarter: str | None = None):
    """
    ODDIY STATEMENTLAR: faqat status=ACCEPTED reportlar.

    DAROMAD: status ne bo'lishidan qat'i nazar, kamida bitta
    quarter_X_status=ACCEPTED bo'lgan reportlar.
    Chunki Daromadda bitta Report'da 4 chorak saqlanadi va
    joriy chorak SAVED/SENT tursa ham oldingi choraklar ACCEPTED bo'lib qoladi.

    quarter berilsa (q1..q4) — faqat shu chorak ACCEPTED bo'lgan reportlar.
    """
    base_qs = (
        Report.objects
        .filter(
            statement=statement,
            deadline_id=deadline_id,
            is_report=True,
            is_general=False,
            is_individual_general=False,
            is_republic=False,
        )
        .select_related("organization")
        .prefetch_related(_prefetch_items_qs())
        .order_by("organization__name")
    )

    if _is_daromad_statement(statement):
        if quarter and quarter in ("q1", "q2", "q3", "q4"):
            q_num = quarter[-1]  # "q2" → "2"
            return base_qs.filter(
                **{f"quarter_{q_num}_status": Report.StatusChoices.ACCEPTED}
            )
        return base_qs.filter(
            Q(quarter_1_status=Report.StatusChoices.ACCEPTED) |
            Q(quarter_2_status=Report.StatusChoices.ACCEPTED) |
            Q(quarter_3_status=Report.StatusChoices.ACCEPTED) |
            Q(quarter_4_status=Report.StatusChoices.ACCEPTED)
        )

    return base_qs.filter(status=Report.StatusChoices.ACCEPTED)


def filter_individual_general_reports_by_deadline(statement, deadline_id: str):
    return (
        Report.objects.filter(
            statement=statement,
            deadline_id=deadline_id,
            is_individual_general=True,
            is_general=False,
            is_republic=False,
            organization__isnull=False,
        )
        .select_related("organization")
        .prefetch_related(_prefetch_items_qs())
        .order_by("organization__name", "-created_at")
    )


def build_individual_general_by_org(individual_generals: list[Report]) -> dict[str, Report]:
    result: dict[str, Report] = {}
    for report in individual_generals:
        if not report.organization_id:
            continue
        org_id = str(report.organization_id)
        if org_id not in result:
            result[org_id] = report
    return result


# ============================================================
# Core aggregation
# ============================================================

def _sum_reports_for_general(
    reports: List[Report],
    cache: StatementDataCache,
    individual_general_by_org: dict[str, Report] | None = None,
    is_daromad: bool = False,
    quarter_filter: str | None = None,
    reja_col_ids: Set[str] | None = None,
) -> Dict[str, Dict[str | None, Decimal]]:
    """
    Region jami uchun qiymatlarni yig'adi.

    DAROMAD:
        - Har report uchun qaysi quarter'lar ACCEPTED ekanligini aniqlaymiz.
        - Faqat ACCEPTED quarter'larning Amalda column'larini summalashga ruxsat beramiz.
        - Reja (status_plan) va is_organization column'lar har doim o'tadi.
        - Birorta ham ACCEPTED quarter yo'q bo'lsa report skip qilinadi.

    ODDIY:
        - Barcha aggregatable column'lar summalanadi.
    """
    totals: Dict[str, Dict[str | None, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    individual_general_by_org = individual_general_by_org or {}

    for report in reports:
        org_id = str(report.organization_id) if report.organization_id else None

        # Daromad: faqat ACCEPTED quarter column'larini ruxsat et
        allowed_col_ids: set[str] | None = None
        if is_daromad:
            if quarter_filter:
                # Faqat tanlangan chorak
                accepted_quarters = [quarter_filter]
            else:
                accepted_quarters = _get_accepted_quarters(report)
            if not accepted_quarters:
                logger.warning(
                    f"[DAROMAD] Report {report.id} da ACCEPTED quarter yo'q, skip."
                )
                continue
            allowed_col_ids = cache.build_daromad_allowed_col_ids(accepted_quarters)

        main_items = {
            str(item.statement_column_id): item
            for item in report.report_items.all()
        }

        individual_items: dict[str, ReportItem] = {}
        ig = individual_general_by_org.get(org_id)
        if ig:
            individual_items = {
                str(item.statement_column_id): item
                for item in ig.report_items.all()
            }

        all_col_ids = set(main_items.keys()) | set(individual_items.keys())

        for col_id in all_col_ids:
            # 1) Calculated column'larni o'tkazib yubor
            if not cache.is_aggregatable(col_id):
                continue

            # 2) Daromad: faqat ruxsat etilgan column'lar
            if allowed_col_ids is not None and col_id not in allowed_col_ids:
                continue

            # 3) Reja source tanlash
            #    status_plan bor column'lar YOKI ordering bo'yicha aniqlangan
            #    global plan reja column'lari individual_general'dan olinadi
            is_reja_source = (
                cache.is_plan_column(col_id)
                or (reja_col_ids and col_id in reja_col_ids)
            )
            if is_reja_source and col_id in individual_items:
                source = individual_items[col_id]
            else:
                source = main_items.get(col_id)

            if not source:
                continue

            for inner in source.inners.all():
                plant_key = str(inner.plant_id) if inner.plant_id else None
                totals[col_id][plant_key] += _safe_decimal(inner.value)

    return totals


# ============================================================
# General / Republic ensure
# ============================================================

def _ensure_general_report(
    statement, deadline_id: str, region_key: str, deadline: Deadline
) -> Optional[Report]:
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
        generals = list(
            Report.objects.filter(
                statement=statement,
                deadline_id=deadline_id,
                region=region_key,
                is_general=True,
                organization__isnull=True,
            ).order_by("-created_at")
        )
        general = generals[0]
        Report.objects.filter(id__in=[g.id for g in generals[1:]]).delete()

    if not general:
        return Report.objects.create(
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


def _ensure_republic_report(
    statement, deadline_id: str, deadline: Deadline
) -> Optional[Report]:
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
        reps = list(
            Report.objects.filter(
                statement=statement,
                deadline_id=deadline_id,
                is_republic=True,
                organization__isnull=True,
            ).order_by("-created_at")
        )
        rep = reps[0]
        Report.objects.filter(id__in=[r.id for r in reps[1:]]).delete()

    if not rep:
        return Report.objects.create(
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


# ============================================================
# Report items bulk create
# ============================================================

def _create_report_items(
    report: Report,
    totals: Dict[str, Dict[str | None, Decimal]],
    org_name_cols: List[str],
    org_name_value: str,
    plant_map: Dict[str, str],
) -> None:
    items_to_create: list[ReportItem] = []
    inners_to_create: list[ReportItemInner] = []

    # 1) Org-name columnlar
    for col_id in org_name_cols:
        items_to_create.append(ReportItem(report=report, statement_column_id=col_id))

    if items_to_create:
        created = ReportItem.objects.bulk_create(items_to_create)
        for item in created:
            inners_to_create.append(ReportItemInner(report_item=item, value=org_name_value))

    # 2) Numeric columnlar
    numeric_items: list[ReportItem] = []
    numeric_cids: list[str] = []

    for cid in totals:
        if cid in org_name_cols:
            continue
        numeric_items.append(ReportItem(report=report, statement_column_id=cid))
        numeric_cids.append(cid)

    created_numeric = ReportItem.objects.bulk_create(numeric_items)

    for item, cid in zip(created_numeric, numeric_cids):
        per_plant = totals[cid]

        plant_keys = sorted(
            (k for k in per_plant if k is not None),
            key=lambda k: plant_map.get(k) or "",
        )
        for pk in plant_keys:
            inners_to_create.append(
                ReportItemInner(report_item=item, plant_id=pk, value=str(per_plant[pk]))
            )
        if None in per_plant:
            inners_to_create.append(
                ReportItemInner(report_item=item, value=str(per_plant[None]))
            )

    if inners_to_create:
        ReportItemInner.objects.bulk_create(inners_to_create, batch_size=1000)


# ============================================================
# Rebuild functions
# ============================================================

@transaction.atomic
def rebuild_general_for_deadline(
    statement,
    deadline: Deadline,
    region_key: str,
    region_reports: List[Report],
    cache: StatementDataCache,
    plant_map: Dict[str, str],
    individual_general_by_org: dict[str, Report] | None = None,
    is_daromad: bool = False,
    quarter_filter: str | None = None,
    reja_col_ids: Set[str] | None = None,
) -> Optional[Report]:
    general = _ensure_general_report(statement, str(deadline.id), region_key, deadline)
    if not general:
        return None

    ReportItem.objects.filter(report=general).delete()

    totals = _sum_reports_for_general(
        reports=region_reports,
        cache=cache,
        individual_general_by_org=individual_general_by_org,
        is_daromad=is_daromad,
        quarter_filter=quarter_filter,
        reja_col_ids=reja_col_ids,
    )

    region_label = str(dict(RegionChoices.choices).get(str(region_key), str(region_key))).title()
    _create_report_items(
        report=general,
        totals=totals,
        org_name_cols=cache.org_name_cols,
        org_name_value=f"{region_label} – Viloyat Jami",
        plant_map=plant_map,
    )

    try:
        general.statement = statement  # duplicate SELECT statement oldini olish
        calculate_general_report(general)
    except Exception as e:
        logger.error(f"[FILTERED][GENERAL] calculate_general_report error: {e}")
    try:
        if getattr(statement, "calculate_expression", None):
            calculate_by_expressions(general)
    except Exception as e:
        logger.error(f"[FILTERED][GENERAL] calculate_by_expressions error: {e}")

    return Report.objects.filter(id=general.id).select_related("organization").prefetch_related(_prefetch_items_qs()).first()


@transaction.atomic
def rebuild_republic_for_deadline(
    statement,
    deadline: Deadline,
    general_reports: List[Report],
    cache: StatementDataCache,
    plant_map: Dict[str, str],
) -> Optional[Report]:
    rep = _ensure_republic_report(statement, str(deadline.id), deadline)
    if not rep:
        return None

    ReportItem.objects.filter(report=rep).delete()

    totals: Dict[str, Dict[str | None, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for gr in general_reports:
        for it in gr.report_items.all():
            cid = str(it.statement_column_id)
            if not cache.is_aggregatable(cid):
                continue
            for inn in it.inners.all():
                plant_key = str(inn.plant_id) if inn.plant_id else None
                totals[cid][plant_key] += _safe_decimal(inn.value)

    _create_report_items(
        report=rep,
        totals=totals,
        org_name_cols=cache.org_name_cols,
        org_name_value="Respublika Jami",
        plant_map=plant_map,
    )

    try:
        rep.statement = statement  # duplicate SELECT statement oldini olish
        calculate_general_report(rep)
    except Exception as e:
        logger.error(f"[FILTERED][REPUBLIC] calculate_general_report error: {e}")
    try:
        if getattr(statement, "calculate_expression", None):
            calculate_by_expressions(rep)
    except Exception as e:
        logger.error(f"[FILTERED][REPUBLIC] calculate_by_expressions error: {e}")

    return Report.objects.filter(id=rep.id).select_related("organization").prefetch_related(_prefetch_items_qs()).first()


# ============================================================
# Serialization
# ============================================================

def _serialize_report_like(
    rep: Report,
    cache: StatementDataCache,
    lang: str,
    plant_map: Dict[str, str],
    org_name_override: Optional[str] = None,
    allowed_col_ids: set[str] | None = None,
) -> Dict:
    org_name = org_name_override
    if org_name is None:
        org_name = get_translated_field(rep.organization, "name", lang) if rep.organization else ""

    statement_columns_payload = []
    # col_id → sum of plant values (for computing percentage row_total later)
    col_totals_map: Dict[str, Decimal] = {}
    # Track which columns are calculated (%, foiz, etc.)
    calculated_col_ids: set[str] = set()

    for it in rep.report_items.all():
        col_id = str(it.statement_column_id)
        # Quarter filter: faqat ruxsat etilgan column'lar
        if allowed_col_ids is not None and col_id not in allowed_col_ids:
            continue
        col_name = cache.get_column_path(col_id, lang)

        inners = list(it.inners.all())
        inners.sort(
            key=lambda x: (0, plant_map.get(str(x.plant_id)) or "") if x.plant_id else (1, "")
        )

        is_org_col = col_id in cache.org_name_cols
        is_calculated = not cache.is_aggregatable(col_id)

        if is_org_col:
            # Tashkilot nomi column — org_name yozish
            inners_payload = [{"value": org_name}]
            row_total = None
        else:
            inners_payload = []
            plant_sum = Decimal("0")
            for inn in inners:
                payload = {"value": inn.value}
                if inn.plant_id:
                    payload["plant_id"] = str(inn.plant_id)
                    payload["plant_name"] = plant_map.get(str(inn.plant_id)) or ""
                    plant_sum += _safe_decimal(inn.value)
                inners_payload.append(payload)

            if is_calculated:
                calculated_col_ids.add(col_id)
                row_total = None  # will be computed after all columns
            else:
                row_total = str(plant_sum.quantize(Decimal("0.01")))
                col_totals_map[col_id] = plant_sum

        col_payload = {
            "statement_column_id": col_id,
            "statement_column_name": col_name,
            "inners": inners_payload,
        }
        if row_total is not None:
            col_payload["row_total"] = row_total
        statement_columns_payload.append(col_payload)

    # ── Calculated columns row_total: (Amalda / Reja) * 100 etc. ──
    # Reja va Amalda column'larini ordering bo'yicha topish
    if calculated_col_ids:
        # col_id → ordering mapping
        col_ordering_map: Dict[str, str] = {}
        ordering_total_map: Dict[str, Decimal] = {}
        for cid, col_obj in cache.all_columns.items():
            ordering = getattr(col_obj, "ordering", "") or ""
            col_ordering_map[cid] = ordering
            if cid in col_totals_map:
                ordering_total_map[ordering] = col_totals_map[cid]

        for col_payload in statement_columns_payload:
            cid = col_payload["statement_column_id"]
            if cid not in calculated_col_ids:
                continue
            ordering = col_ordering_map.get(cid, "")
            # Foizda column: ordering 1.1.5 → (1.1.3 / 1.1.2) * 100
            # Farq column: ordering 1.1.4 → 1.1.3 - 1.1.2
            # Chorak farq: 1.X.1.3 → 1.X.1.2 - 1.X.1.1
            row_total_val = Decimal("0")
            if ordering == "1.1.5":
                reja = ordering_total_map.get("1.1.2", Decimal("0"))
                amalda = ordering_total_map.get("1.1.3", Decimal("0"))
                if reja:
                    row_total_val = (amalda / reja * 100).quantize(Decimal("0.01"))
            elif ordering == "1.1.4":
                amalda = ordering_total_map.get("1.1.3", Decimal("0"))
                reja = ordering_total_map.get("1.1.2", Decimal("0"))
                row_total_val = (amalda - reja).quantize(Decimal("0.01"))
            elif ordering.endswith(".1.3"):
                # Chorak farq: X.Y.1.3 = X.Y.1.2 - X.Y.1.1
                prefix = ordering[:-1]  # "X.Y.1."
                ch_amalda = ordering_total_map.get(f"{prefix}2", Decimal("0"))
                ch_reja = ordering_total_map.get(f"{prefix}1", Decimal("0"))
                row_total_val = (ch_amalda - ch_reja).quantize(Decimal("0.01"))
            else:
                # Boshqa calculated column → sum (fallback)
                plant_sum = Decimal("0")
                for inn_data in col_payload.get("inners", []):
                    plant_sum += _safe_decimal(inn_data.get("value", "0"))
                row_total_val = plant_sum.quantize(Decimal("0.01"))

            col_payload["row_total"] = str(row_total_val)

    # ── Virtual "O'simlik nomi" ustuni (plant-based statementlar uchun) ──
    # use_plant_plan flag'iga yoki inners ichida plant_id borligiga qarab aniqlanadi
    all_plants: Dict[str, str] = {}
    for col_data in statement_columns_payload:
        for inn in col_data.get("inners", []):
            pid = inn.get("plant_id")
            if pid and pid not in all_plants:
                all_plants[pid] = inn.get("plant_name", "")

    if all_plants:
        stmt_name = (statement.name_uz or statement.name or "").lower()
        if "daromad" in stmt_name:
            plant_name_label = "Источники дохода" if lang == "ru" else "Daromad manbalari"
        else:
            plant_name_label = "Название растения" if lang == "ru" else "O'simlik nomi"
        
        plant_inners = [
            {"plant_id": pid, "plant_name": pname, "value": pname}
            for pid, pname in sorted(all_plants.items(), key=lambda x: x[1])
        ]
        plant_col = {
            "statement_column_id": "plant_name_virtual",
            "statement_column_name": plant_name_label,
            "is_virtual": True,
            "inners": plant_inners,
        }
        # Tashkilot nomi'dan keyin insert qilish
        insert_idx = 0
        for i, c in enumerate(statement_columns_payload):
            if c.get("statement_column_id") in cache.org_name_cols:
                insert_idx = i + 1
                break
        statement_columns_payload.insert(insert_idx, plant_col)


    org_id_str = str(rep.organization_id) if rep.organization_id else None
    return {
        "id": str(rep.id),
        "organization": org_id_str,
        "organization_name": org_name,
        "statement": str(rep.statement_id),
        "deadline": str(rep.deadline_id) if rep.deadline_id else None,
        "report_items": [{
            "organization_id": org_id_str,
            "organization_name": org_name,
            "statement_columns": statement_columns_payload,
        }],
        "is_general": rep.is_general,
        "is_individual_general": rep.is_individual_general,
        "is_republic": rep.is_republic,
    }


# ============================================================
# Main entry point
# ============================================================

def build_filtered_payload(statement, deadline_id: str, lang: str, quarter: str | None = None) -> Dict:
    """
    Daromad va oddiy statementlar uchun filtered aggregation.

    Asosiy o'zgarishlar:
    - StatementDataCache singleton emas — har request yangi instance.
    - lru_cache olib tashlandi — Django model instance hashable emas.
    - Daromad uchun quarter-aware aggregation: faqat ACCEPTED
      quarter'larning Amalda column'lari summalanadi.
    - plant_map bir marta yuklanadi va hamma joyga uzatiladi.
    - Redis cache: natija 5 daqiqa saqlanadi, signal bilan invalidate qilinadi.
    """

    # ─── Redis cache check ───
    from apps.reports.services.report_cache import (
        get_cached_filtered_payload,
        set_cached_filtered_payload,
    )
    stmt_id = str(statement.id)
    cached = get_cached_filtered_payload(stmt_id, deadline_id, lang, quarter)
    if cached is not None:
        return cached

    # 1) Cache — request-scoped, singleton emas
    cache = StatementDataCache(str(statement.id))
    cache.load()

    # 2) Deadline — bir marta
    deadline = Deadline.objects.filter(id=deadline_id).first()
    if not deadline:
        return {"count": 0, "next": None, "previous": None, "results": []}

    # 3) Reportlarni yuklash
    is_daromad = _is_daromad_statement(statement)
    individuals = list(filter_reports_by_deadline(statement, deadline_id, quarter=quarter))

    # 4) Individual general (maxsus statementlar uchun)
    individual_general_by_org: dict[str, Report] = {}
    reja_col_ids: Set[str] = set()
    if should_use_individual_general_plan_source(statement):
        igs = list(filter_individual_general_reports_by_deadline(statement, deadline_id))
        individual_general_by_org = build_individual_general_by_org(igs)
        reja_col_ids = _get_global_plan_reja_col_ids(statement, cache)

    # 5) Plant map — bir marta barcha reportlar uchun
    all_plant_ids: set[str] = set()
    for rep in individuals:
        for it in rep.report_items.all():
            for inn in it.inners.all():
                if inn.plant_id:
                    all_plant_ids.add(str(inn.plant_id))

    plant_map: Dict[str, str] = {}
    # lang ga qarab name_uz yoki name_ru olinadi
    plant_name_field = f"name_{lang}" if lang in ("uz", "ru") else "name_uz"
    if all_plant_ids:
        plant_db = Plant.objects.filter(id__in=all_plant_ids).values_list("id", plant_name_field, "name")
        plant_map = {str(pk): (localized or fallback or "") for pk, localized, fallback in plant_db}

    # 6) Regionlar bo'yicha guruhlash
    by_region: Dict[str, List[Report]] = defaultdict(list)
    for rep in individuals:
        region_key = str(getattr(rep.organization, "region", "") or "")
        if region_key:
            by_region[region_key].append(rep)

    results = []
    region_general_reports: List[Report] = []

    # Daromad + quarter filter: faqat shu chorak ustunlari ko'rinadi
    serialize_allowed: set[str] | None = None
    if is_daromad and quarter:
        serialize_allowed = cache.build_daromad_allowed_col_ids([quarter])
        # Yillik summary columns ham ko'rinishi kerak (Reja, Amalda, Farqi, Foizda)
        # General reportda calculator Q1 datadan qayta hisoblagan, shuning uchun to'g'ri
        for yillik_ordering in ("1.1.2", "1.1.3", "1.1.4", "1.1.5"):
            col_id = cache.get_col_id_by_ordering(yillik_ordering)
            if col_id:
                serialize_allowed.add(col_id)

    # 7) Har bir region uchun general rebuild
    region_choices_map = dict(RegionChoices.choices)
    for region_key, reps in by_region.items():
        region_label = region_choices_map.get(str(region_key), str(region_key)).title()

        general_rep = rebuild_general_for_deadline(
            statement=statement,
            deadline=deadline,
            region_key=region_key,
            region_reports=reps,
            cache=cache,
            plant_map=plant_map,
            individual_general_by_org=individual_general_by_org,
            is_daromad=is_daromad,
            quarter_filter=quarter,
            reja_col_ids=reja_col_ids,
        )
        if general_rep:
            region_general_reports.append(general_rep)

        children_payload = []
        for r in reps:
            s = _serialize_report_like(r, cache, lang, plant_map, allowed_col_ids=serialize_allowed)
            children_payload.append({
                "id": s["id"],
                "organization_name": s["organization_name"],
                "report_items": s["report_items"],
                "sent_by_full_name": None,
                "sent_by_org_name": s["organization_name"],
                "sent_by_role": None,
            })

        if general_rep:
            parent = _serialize_report_like(
                general_rep, cache, lang, plant_map,
                org_name_override=f"{region_label} – Viloyat Jami",
                allowed_col_ids=serialize_allowed,
            )
            results.append({
                "id": parent["id"],
                "organization_name": parent["organization_name"] or f"{region_label} – Viloyat Jami",
                "report_items": parent["report_items"],
                "children_reports": children_payload,
            })
        else:
            results.append({
                "id": None,
                "organization_name": f"{region_label} – Viloyat Jami",
                "report_items": [{"organization_id": "general",
                                  "organization_name": f"{region_label} – Viloyat Jami",
                                  "statement_columns": []}],
                "children_reports": children_payload,
            })

    # 8) Republic rebuild
    if region_general_reports:
        # Republic uchun plant_map ni general_rep itemlardan ham to'ldirish
        for gr in region_general_reports:
            for it in gr.report_items.all():
                for inn in it.inners.all():
                    if inn.plant_id and str(inn.plant_id) not in plant_map:
                        all_plant_ids.add(str(inn.plant_id))

        if all_plant_ids - set(plant_map.keys()):
            extra_db = Plant.objects.filter(
                id__in=all_plant_ids - set(plant_map.keys())
            ).values_list("id", plant_name_field, "name")
            extra = {str(pk): (localized or fallback or "") for pk, localized, fallback in extra_db}
            plant_map.update(extra)

        republic_rep = rebuild_republic_for_deadline(
            statement=statement,
            deadline=deadline,
            general_reports=region_general_reports,
            cache=cache,
            plant_map=plant_map,
        )
        if republic_rep:
            rp = _serialize_report_like(
                republic_rep, cache, lang, plant_map,
                org_name_override="Respublika Jami",
                allowed_col_ids=serialize_allowed,
            )
            results.append({
                "id": rp["id"],
                "organization_name": rp["organization_name"] or "Respublika Jami",
                "report_items": rp["report_items"],
                "children_reports": [],
            })
        else:
            results.append({
                "id": None,
                "organization_name": "Respublika Jami",
                "report_items": [{"organization_id": "republic",
                                  "organization_name": "Respublika Jami",
                                  "statement_columns": []}],
                "children_reports": [],
            })

    result = {"count": len(results), "next": None, "previous": None, "results": results}

    # ─── Redis cache set ───
    set_cached_filtered_payload(stmt_id, deadline_id, lang, quarter, result)

    return result