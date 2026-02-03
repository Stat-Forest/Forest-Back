from decimal import Decimal, InvalidOperation
from collections import defaultdict
from django.db import transaction, connection

from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn
from apps.reports.services.get_two_numbers_in_percent import round_decimal


# ------------------ HELPERS ------------------

def normalize(val) -> Decimal:
    try:
        if val in (None, ""):
            return Decimal("0")
        return Decimal(str(val))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


Q2 = Decimal("1.00")


def q2(v: Decimal) -> Decimal:
    return (v or Decimal("0")).quantize(Q2)


# ------------------ MAIN ------------------

def calculate_daromad_plant_based(report: Report, pre: dict | None = None):
    start_q = len(connection.queries)
    # Prepare data
    if pre is None:
        # 1️⃣ STATEMENT COLUMNS — ONLY ONCE
        columns = list(
            StatementColumn.objects
            .filter(statement=report.statement)
            .only("id", "ordering", "is_organization")
        )
        column_by_ordering = {c.ordering: c for c in columns}
        column_ids = {c.id for c in columns}

        # 2️⃣ REPORT ITEMS — ONLY ONCE
        report_items = list(
            ReportItem.objects
            .filter(report=report, statement_column_id__in=column_ids)
            .only("id", "statement_column_id")
        )
        item_by_column_id = {it.statement_column_id: it for it in report_items}

        # 🔑 MUHIM: item_id → ordering map
        ordering_by_item_id = {
            it.id: next(
                c.ordering for c in columns if c.id == it.statement_column_id
            )
            for it in report_items
        }

        # 3️⃣ INNERS — ONLY ONCE
        inners = list(
            ReportItemInner.objects
            .filter(report_item__report=report)
            .only("id", "report_item_id", "plant_id", "value")
        )
    else:
        # Use preloaded maps
        column_by_ordering = pre.get("columns_by_ordering", {})
        item_by_column_id = pre.get("items_by_column_id", {})
        ordering_by_item_id = pre.get("ordering_by_item_id", {})
        inners = pre.get("inners", [])

    values = defaultdict(lambda: defaultdict(Decimal))
    org_values = defaultdict(Decimal)
    inner_map = {}

    for inner in inners:
        ordering = ordering_by_item_id.get(inner.report_item_id)
        if not ordering:
            continue

        val = normalize(inner.value)
        key = (ordering, inner.plant_id)
        inner_map[key] = inner

        if inner.plant_id is None:
            org_values[ordering] += val
        else:
            values[ordering][inner.plant_id] += val

    # ------------------ BUFFERLAR ------------------

    new_items = []
    pending_inners = []
    update_inners = {}
    pending_keys = set()

    def ensure_item(column_id):
        if column_id not in item_by_column_id:
            item = ReportItem(report=report, statement_column_id=column_id)
            item_by_column_id[column_id] = item
            new_items.append(item)

    def set_value(ordering, plant_id, value):
        column = column_by_ordering.get(ordering)
        if not column:
            return

        if column.is_organization:
            plant_id = None

        value = q2(value)
        ensure_item(column.id)

        key = (ordering, plant_id)
        existing = inner_map.get(key)

        if existing:
            if normalize(existing.value) != value:
                existing.value = str(value)
                update_inners[existing.id] = existing
        else:
            if key not in pending_keys:
                pending_keys.add(key)
                pending_inners.append((column.id, plant_id, str(value)))
            inner_map[key] = None

        if plant_id is None:
            org_values[ordering] = value
        else:
            values[ordering][plant_id] = value

    # ------------------ CALCULATIONS (O‘ZGARMAGAN) ------------------
    chorak_map = {
        "1.3.1.2": ["1.3.2.1.2", "1.3.2.2.2", "1.3.2.3.2"],
        "1.4.1.2": ["1.4.2.1.2", "1.4.2.2.2", "1.4.2.3.2"],
        "1.5.1.2": ["1.5.2.1.2", "1.5.2.2.2", "1.5.2.3.2"],
        "1.6.1.2": ["1.6.2.1.2", "1.6.2.2.2", "1.6.2.3.2"],
    }

    chorak_reja = ["1.3.1.1", "1.4.1.1", "1.5.1.1", "1.6.1.1"]

    all_plant_ids = {
        pid for m in values.values() for pid in m.keys()
    }

    for plant_id in all_plant_ids:
        for chorak_amalda, months in chorak_map.items():
            amalda = sum(values[m][plant_id] for m in months)
            set_value(chorak_amalda, plant_id, amalda)

            reja = org_values[chorak_amalda.replace(".2", ".1")]
            set_value(chorak_amalda.replace(".2", ".3"), plant_id, reja - amalda)

    yil_reja = sum(org_values[o] for o in chorak_reja)
    yil_amalda = sum(sum(values[o].values()) for o in chorak_map)

    set_value("1.1.2", None, yil_reja)
    set_value("1.1.3", None, yil_amalda)
    set_value("1.1.4", None, yil_reja - yil_amalda)

    foiz = round_decimal((yil_amalda / yil_reja) * 100, 1) if yil_reja else Decimal("0")
    set_value("1.1.5", None, foiz)

    # ------------------ SAVE (NO DUPLICATES) ------------------

    with transaction.atomic():
        if new_items:
            ReportItem.objects.bulk_create(new_items)

        if pending_inners:
            ReportItemInner.objects.bulk_create([
                ReportItemInner(
                    report_item=item_by_column_id[col_id],
                    plant_id=plant_id,
                    value=value
                )
                for col_id, plant_id, value in pending_inners
            ])

        if update_inners:
            ReportItemInner.objects.bulk_update(update_inners.values(), ["value"])

    print(f"✅ Daromad calc done. Queries: {len(connection.queries) - start_q}")
