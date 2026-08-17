import logging
from decimal import Decimal, InvalidOperation
from collections import defaultdict

from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn
from apps.reports.services.get_two_numbers_in_percent import round_decimal

logger = logging.getLogger(__name__)


# =====================================================
# Utils
# =====================================================

def normalize(value):
    try:
        if value is None or value == "":
            return Decimal("0")
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def safe_percent(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return round_decimal((numerator / denominator) * Decimal("100"), places=1)


# =====================================================
# PRELOAD DATA
# =====================================================

def preload_plant_values_by_ordering(report: Report):
    """
    ordering -> {plant_id -> Decimal}
    """
    result = defaultdict(lambda: defaultdict(Decimal))

    inners = (
        ReportItemInner.objects
        .filter(report_item__report=report)
        .select_related("report_item__statement_column")
    )

    for inner in inners:
        ordering = inner.report_item.statement_column.ordering
        if inner.plant_id:
            result[ordering][inner.plant_id] += normalize(inner.value)

    return result


def preload_statement_columns_and_items(report: Report):
    """
    Columnlar + ReportItemlar + INNER OBJECT CACHE
    """
    columns = {
        col.ordering: col
        for col in StatementColumn.objects.filter(statement=report.statement)
    }

    report_items = list(
        ReportItem.objects
        .filter(report=report)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    report_item_map = {
        item.statement_column_id: item
        for item in report_items
    }

    # column_id -> {plant_id -> inner object}
    # column.id kalit sifatida ishlatiladi (item.id emas!)
    # chunki yangi yaratilgan ReportItem.id None bo'ladi
    inner_cache = {
        item.statement_column_id: {inner.plant_id: inner for inner in item.inners.all()}
        for item in report_items
    }

    return columns, report_item_map, inner_cache


# =====================================================
# CORE CREATOR (plant-based)
# =====================================================

def create_plant_values(
    report,
    column,
    plant_totals,
    report_item_map,
    inner_cache,
    create_buffer,
    update_buffer
):
    """
    Har bir o'simlik uchun inner yaratadi yoki yangilaydi.
    """
    # ReportItem
    item = report_item_map.get(column.id)

    if not item:
        item = ReportItem(report=report, statement_column=column)
        report_item_map[column.id] = item
        create_buffer["report_items"].append(item)
        inner_cache[column.id] = {}

    # column.id orqali cache'dan olish (item.id emas!)
    old_inners = inner_cache.get(column.id, {})

    # Inners — har bir o'simlik uchun
    for plant_id, new_val in plant_totals.items():
        new_val = normalize(new_val)

        if plant_id not in old_inners:
            # CREATE
            create_buffer["inners"].append(
                ReportItemInner(
                    report_item=item,
                    plant_id=plant_id,
                    value=str(new_val)
                )
            )
        else:
            # UPDATE
            obj = old_inners[plant_id]
            if normalize(obj.value) != new_val:
                obj.value = str(new_val)
                update_buffer["inners"].append(obj)


# =====================================================
# MAIN CALCULATOR
# =====================================================

def calculate_seed_plants(report: Report):
    """
    Hisobot: 1-ilova (Niholxona va Ko'chatxona Jami)
    PLANT-BASED hisoblash — har bir o'simlik uchun alohida.

    Hisoblanadigan ustunlar:
    - 1.1.2.2 = 1.1.3.1.2 + 1.1.3.2.2       (Amalda Jami = Niholxona Amalda + Ko'chatxona Amalda)
    - 1.1.2.3 = 1.1.2.2 / 1.1.2.1 * 100      (Foiz Jami)
    - 1.1.3.1.3 = 1.1.3.1.2 / 1.1.3.1.1 * 100 (Niholxona Foiz)
    - 1.1.3.2.3 = 1.1.3.2.2 / 1.1.3.2.1 * 100 (Ko'chatxona Foiz)
    """

    columns, report_item_map, inner_cache = preload_statement_columns_and_items(report)
    plant_values_map = preload_plant_values_by_ordering(report)

    create_buffer = {
        "report_items": [],
        "inners": []
    }
    update_buffer = {
        "inners": []
    }

    # -------------------------------------------------------
    # 1.1.2.2 = 1.1.3.1.2 + 1.1.3.2.2 (Amalda Jami per plant)
    # -------------------------------------------------------
    niholxona_amalda = plant_values_map.get("1.1.3.1.2", {})
    kochatxona_amalda = plant_values_map.get("1.1.3.2.2", {})

    all_plant_ids = set(niholxona_amalda) | set(kochatxona_amalda)

    amalda_jami = defaultdict(Decimal)
    for pid in all_plant_ids:
        amalda_jami[pid] = niholxona_amalda.get(pid, Decimal("0")) + kochatxona_amalda.get(pid, Decimal("0"))

    if "1.1.2.2" in columns:
        create_plant_values(
            report, columns["1.1.2.2"], amalda_jami,
            report_item_map, inner_cache, create_buffer, update_buffer
        )

    # -------------------------------------------------------
    # 1.1.3.1.3 = 1.1.3.1.2 / 1.1.3.1.1 * 100 (Niholxona Foiz per plant)
    # -------------------------------------------------------
    niholxona_reja = plant_values_map.get("1.1.3.1.1", {})
    niholxona_foiz = {}
    for pid in set(niholxona_amalda) | set(niholxona_reja):
        niholxona_foiz[pid] = safe_percent(
            niholxona_amalda.get(pid, Decimal("0")),
            niholxona_reja.get(pid, Decimal("0"))
        )

    if "1.1.3.1.3" in columns:
        create_plant_values(
            report, columns["1.1.3.1.3"], niholxona_foiz,
            report_item_map, inner_cache, create_buffer, update_buffer
        )

    # -------------------------------------------------------
    # 1.1.3.2.3 = 1.1.3.2.2 / 1.1.3.2.1 * 100 (Ko'chatxona Foiz per plant)
    # -------------------------------------------------------
    kochatxona_reja = plant_values_map.get("1.1.3.2.1", {})
    kochatxona_foiz = {}
    for pid in set(kochatxona_amalda) | set(kochatxona_reja):
        kochatxona_foiz[pid] = safe_percent(
            kochatxona_amalda.get(pid, Decimal("0")),
            kochatxona_reja.get(pid, Decimal("0"))
        )

    if "1.1.3.2.3" in columns:
        create_plant_values(
            report, columns["1.1.3.2.3"], kochatxona_foiz,
            report_item_map, inner_cache, create_buffer, update_buffer
        )

    # -------------------------------------------------------
    # 1.1.2.3 = 1.1.2.2 / 1.1.2.1 * 100 (Jami Foiz per plant)
    # -------------------------------------------------------
    reja_jami = plant_values_map.get("1.1.2.1", {})
    foiz_jami = {}
    for pid in set(amalda_jami) | set(reja_jami):
        foiz_jami[pid] = safe_percent(
            amalda_jami.get(pid, Decimal("0")),
            reja_jami.get(pid, Decimal("0"))
        )

    if "1.1.2.3" in columns:
        create_plant_values(
            report, columns["1.1.2.3"], foiz_jami,
            report_item_map, inner_cache, create_buffer, update_buffer
        )

    # -------------------------------------------------------
    # BULK SAVE
    # -------------------------------------------------------
    if create_buffer["report_items"]:
        ReportItem.objects.bulk_create(create_buffer["report_items"])

    if create_buffer["inners"]:
        ReportItemInner.objects.bulk_create(create_buffer["inners"])

    if update_buffer["inners"]:
        ReportItemInner.objects.bulk_update(update_buffer["inners"], ["value"])

    logger.info(
        "calculate_seed_plants: %d items created, %d inners created, %d inners updated",
        len(create_buffer["report_items"]),
        len(create_buffer["inners"]),
        len(update_buffer["inners"]),
    )
