from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.db import transaction, connection

from apps.reports.services.get_two_numbers_in_percent import round_decimal
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn


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


def calculate_daromad_plant_based(report: Report, pre: dict | None = None):
    """
    Daromad plant-based calculator.

    Optimizations:
    - column_id -> ordering map oldindan quriladi
    - item/order mapping O(n^2) emas
    - pre yubilsa qayta query qilmaydi
    """
    start_q = len(connection.queries)

    if pre is None:
        columns = list(
            StatementColumn.objects
            .filter(statement=report.statement)
            .only("id", "ordering", "is_organization")
        )
        column_by_ordering = {c.ordering: c for c in columns}
        column_id_to_ordering = {c.id: c.ordering for c in columns}
        column_ids = list(column_id_to_ordering.keys())

        report_items = list(
            ReportItem.objects
            .filter(report=report, statement_column_id__in=column_ids)
            .only("id", "statement_column_id")
        )
        item_by_column_id = {it.statement_column_id: it for it in report_items}
        ordering_by_item_id = {
            it.id: column_id_to_ordering.get(it.statement_column_id)
            for it in report_items
        }

        inners = list(
            ReportItemInner.objects
            .filter(report_item__report=report)
            .only("id", "report_item_id", "plant_id", "value")
        )
    else:
        column_by_ordering = pre.get("columns_by_ordering", {})
        item_by_column_id = pre.get("items_by_column_id", {})
        ordering_by_item_id = pre.get("ordering_by_item_id", {})
        inners = pre.get("inners", [])

    values = defaultdict(lambda: defaultdict(Decimal))
    inner_map = {}

    non_plant_based_orderings = {"1.1.3", "1.1.4", "1.1.5"}
    plant_based_yillik_reja = {"1.1.2"}

    plant_based_column_ids = {
        c.id for c in column_by_ordering.values()
        if not c.is_organization and (
            c.ordering not in non_plant_based_orderings or
            c.ordering in plant_based_yillik_reja
        )
    }

    deleted_count = ReportItemInner.objects.filter(
        report_item__report=report,
        report_item__statement_column_id__in=plant_based_column_ids,
        plant_id__isnull=True,
    ).delete()

    if deleted_count and deleted_count[0]:
        print(f"🗑️ Deleted {deleted_count[0]} orphan inners")

    for inner in inners:
        ordering = ordering_by_item_id.get(inner.report_item_id)
        if not ordering:
            continue

        column = column_by_ordering.get(ordering)
        if column and not column.is_organization:
            if inner.plant_id is None and ordering not in non_plant_based_orderings:
                continue

        val = normalize(inner.value)
        key = (ordering, inner.plant_id)
        inner_map[key] = inner
        values[ordering][inner.plant_id] = val

    new_items = []
    pending_inners = []
    update_inners = {}
    pending_keys = set()

    def ensure_item(column_id):
        item = item_by_column_id.get(column_id)
        if item is None:
            item = ReportItem(report=report, statement_column_id=column_id)
            item_by_column_id[column_id] = item
            new_items.append(item)
        return item

    def set_value(ordering, plant_id, value):
        column = column_by_ordering.get(ordering)
        if not column:
            return

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

        values[ordering][plant_id] = value

    chorak_map = {
        "1.3.1.2": ["1.3.2.1.2", "1.3.2.2.2", "1.3.2.3.2"],
        "1.4.1.2": ["1.4.2.1.2", "1.4.2.2.2", "1.4.2.3.2"],
        "1.5.1.2": ["1.5.2.1.2", "1.5.2.2.2", "1.5.2.3.2"],
        "1.6.1.2": ["1.6.2.1.2", "1.6.2.2.2", "1.6.2.3.2"],
    }
    chorak_reja_orderings = ["1.3.1.1", "1.4.1.1", "1.5.1.1", "1.6.1.1"]
    chorak_farq_orderings = ["1.3.1.3", "1.4.1.3", "1.5.1.3", "1.6.1.3"]

    all_plant_ids = {
        pid
        for ordering_dict in values.values()
        for pid in ordering_dict.keys()
        if pid is not None
    }

    for plant_id in all_plant_ids:
        for idx, (chorak_amalda, months) in enumerate(chorak_map.items()):
            amalda = sum(values[m][plant_id] for m in months)
            set_value(chorak_amalda, plant_id, amalda)

            chorak_reja_ordering = chorak_reja_orderings[idx]
            reja = values[chorak_reja_ordering].get(plant_id, Decimal("0"))

            chorak_farq_ordering = chorak_farq_orderings[idx]
            set_value(chorak_farq_ordering, plant_id, amalda - reja)

    for plant_id in all_plant_ids:
        yil_reja_plant = Decimal("0")
        for chorak_reja in chorak_reja_orderings:
            yil_reja_plant += values[chorak_reja].get(plant_id, Decimal("0"))
        set_value("1.1.2", plant_id, yil_reja_plant)

    yil_reja_total = Decimal("0")
    yil_amalda_total = Decimal("0")

    for plant_id in all_plant_ids:
        yil_reja_total += values["1.1.2"].get(plant_id, Decimal("0"))
        yil_amalda_total += sum(
            values[chorak_amalda].get(plant_id, Decimal("0"))
            for chorak_amalda in chorak_map.keys()
        )

    set_value("1.1.3", None, yil_amalda_total)
    set_value("1.1.4", None, yil_amalda_total - yil_reja_total)

    if yil_reja_total:
        foiz_total = round_decimal((yil_amalda_total / yil_reja_total) * 100, 1)
    else:
        foiz_total = Decimal("0")
    set_value("1.1.5", None, foiz_total)

    with transaction.atomic():
        if new_items:
            ReportItem.objects.bulk_create(new_items)

        if pending_inners:
            refreshed_items = {
                it.statement_column_id: it
                for it in ReportItem.objects.filter(
                    report=report,
                    statement_column_id__in=[col_id for col_id, _, _ in pending_inners]
                ).only("id", "statement_column_id")
            }
            item_by_column_id.update(refreshed_items)

            ReportItemInner.objects.bulk_create([
                ReportItemInner(
                    report_item=item_by_column_id[col_id],
                    plant_id=plant_id,
                    value=value,
                )
                for col_id, plant_id, value in pending_inners
            ])

        if update_inners:
            ReportItemInner.objects.bulk_update(update_inners.values(), ["value"])

    print(f"✅ Daromad calc done. Queries: {len(connection.queries) - start_q}")