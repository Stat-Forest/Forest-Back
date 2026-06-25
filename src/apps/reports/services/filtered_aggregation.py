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

def filter_reports_by_deadline(statement, deadline_id: str):
    """
    ODDIY STATEMENTLAR: faqat status=ACCEPTED reportlar.

    DAROMAD: status ne bo'lishidan qat'i nazar, kamida bitta
    quarter_X_status=ACCEPTED bo'lgan reportlar.
    Chunki Daromadda bitta Report'da 4 chorak saqlanadi va
    joriy chorak SAVED/SENT tursa ham oldingi choraklar ACCEPTED bo'lib qoladi.
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
            if cache.is_plan_column(col_id) and col_id in individual_items:
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
            key=lambda k: plant_map.get(k, ""),
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
    )

    region_label = dict(RegionChoices.choices).get(str(region_key), str(region_key))
    _create_report_items(
        report=general,
        totals=totals,
        org_name_cols=cache.org_name_cols,
        org_name_value=f"{region_label} – Viloyat Jami",
        plant_map=plant_map,
    )

    try:
        calculate_general_report(general)
    except Exception as e:
        logger.error(f"[FILTERED][GENERAL] calculate_general_report error: {e}")
    try:
        if getattr(general.statement, "calculate_expression", None):
            calculate_by_expressions(general)
    except Exception as e:
        logger.error(f"[FILTERED][GENERAL] calculate_by_expressions error: {e}")

    return Report.objects.filter(id=general.id).prefetch_related(_prefetch_items_qs()).first()


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
        calculate_general_report(rep)
    except Exception as e:
        logger.error(f"[FILTERED][REPUBLIC] calculate_general_report error: {e}")
    try:
        if getattr(rep.statement, "calculate_expression", None):
            calculate_by_expressions(rep)
    except Exception as e:
        logger.error(f"[FILTERED][REPUBLIC] calculate_by_expressions error: {e}")

    return Report.objects.filter(id=rep.id).prefetch_related(_prefetch_items_qs()).first()


# ============================================================
# Serialization
# ============================================================

def _serialize_report_like(
    rep: Report,
    cache: StatementDataCache,
    lang: str,
    plant_map: Dict[str, str],
    org_name_override: Optional[str] = None,
) -> Dict:
    org_name = org_name_override
    if org_name is None:
        org_name = get_translated_field(rep.organization, "name", lang) if rep.organization else ""

    statement_columns_payload = []
    for it in rep.report_items.all():
        col_id = str(it.statement_column_id)
        col_name = cache.get_column_path(col_id, lang)

        inners = list(it.inners.all())
        inners.sort(
            key=lambda x: (0, plant_map.get(str(x.plant_id), "")) if x.plant_id else (1, "")
        )

        inners_payload = []
        for inn in inners:
            payload = {"value": inn.value}
            if inn.plant_id:
                payload["plant_id"] = str(inn.plant_id)
                payload["plant_name"] = plant_map.get(str(inn.plant_id), "")
            inners_payload.append(payload)

        statement_columns_payload.append({
            "statement_column_id": col_id,
            "statement_column_name": col_name,
            "inners": inners_payload,
        })

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

def build_filtered_payload(statement, deadline_id: str, lang: str) -> Dict:
    """
    Daromad va oddiy statementlar uchun filtered aggregation.

    Asosiy o'zgarishlar:
    - StatementDataCache singleton emas — har request yangi instance.
    - lru_cache olib tashlandi — Django model instance hashable emas.
    - Daromad uchun quarter-aware aggregation: faqat ACCEPTED
      quarter'larning Amalda column'lari summalanadi.
    - plant_map bir marta yuklanadi va hamma joyga uzatiladi.
    """

    # 1) Cache — request-scoped, singleton emas
    cache = StatementDataCache(str(statement.id))
    cache.load()

    # 2) Deadline — bir marta
    deadline = Deadline.objects.filter(id=deadline_id).first()
    if not deadline:
        return {"count": 0, "next": None, "previous": None, "results": []}

    # 3) Reportlarni yuklash
    is_daromad = _is_daromad_statement(statement)
    individuals = list(filter_reports_by_deadline(statement, deadline_id))

    # 4) Individual general (maxsus statementlar uchun)
    individual_general_by_org: dict[str, Report] = {}
    if should_use_individual_general_plan_source(statement):
        igs = list(filter_individual_general_reports_by_deadline(statement, deadline_id))
        individual_general_by_org = build_individual_general_by_org(igs)

    # 5) Plant map — bir marta barcha reportlar uchun
    all_plant_ids: set[str] = set()
    for rep in individuals:
        for it in rep.report_items.all():
            for inn in it.inners.all():
                if inn.plant_id:
                    all_plant_ids.add(str(inn.plant_id))

    plant_map: Dict[str, str] = {}
    if all_plant_ids:
        plant_map = dict(Plant.objects.filter(id__in=all_plant_ids).values_list("id", "name"))

    # 6) Regionlar bo'yicha guruhlash
    by_region: Dict[str, List[Report]] = defaultdict(list)
    for rep in individuals:
        region_key = str(getattr(rep.organization, "region", "") or "")
        if region_key:
            by_region[region_key].append(rep)

    results = []
    region_general_reports: List[Report] = []

    # 7) Har bir region uchun general rebuild
    for region_key, reps in by_region.items():
        general_rep = rebuild_general_for_deadline(
            statement=statement,
            deadline=deadline,
            region_key=region_key,
            region_reports=reps,
            cache=cache,
            plant_map=plant_map,
            individual_general_by_org=individual_general_by_org,
            is_daromad=is_daromad,
        )
        if general_rep:
            region_general_reports.append(general_rep)

        children_payload = []
        for r in reps:
            s = _serialize_report_like(r, cache, lang, plant_map)
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
                org_name_override=f"{region_key} – Viloyat Jami",
            )
            results.append({
                "id": parent["id"],
                "organization_name": parent["organization_name"] or f"{region_key} – Viloyat Jami",
                "report_items": parent["report_items"],
                "children_reports": children_payload,
            })
        else:
            results.append({
                "id": None,
                "organization_name": f"{region_key} – Viloyat Jami",
                "report_items": [{"organization_id": "general",
                                  "organization_name": f"{region_key} – Viloyat Jami",
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
            extra = dict(
                Plant.objects.filter(
                    id__in=all_plant_ids - set(plant_map.keys())
                ).values_list("id", "name")
            )
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

    return {"count": len(results), "next": None, "previous": None, "results": results}