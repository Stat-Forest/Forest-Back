from decimal import Decimal, InvalidOperation
from collections import defaultdict

from django.db import connection

from apps.reports.models import (
    Report,
    ReportItem,
    ReportItemInner,
    StatementColumn,
)
from apps.reports.services.get_two_numbers_in_percent import round_decimal


def normalize(val) -> Decimal:
    try:
        if val in (None, ""):
            return Decimal("0")
        return Decimal(str(val))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def calculate_daromad_plant_based(report: Report):
    """
    OPTIMIZED VERSION with QUERY DEBUGGING
    - Query sonini kuzatish qo'shildi (print orqali)
    - Foydalanuvchi: funksiyani ishlatganda terminalga chiqadigan ma'lumotlarni yuboring.
    """

    # Query logging boshlanishi
    initial_queries = len(connection.queries)
    print(f"START: {initial_queries} queries")

    # 1. PRELOAD ALL COLUMNS (bitta query)
    #    IMPORTANT: We fully materialize and build maps so we never touch
    #    StatementColumn inside loops, eliminating N+1 lookups by id.
    columns = list(StatementColumn.objects.filter(statement=report.statement))
    column_by_id = {c.id: c for c in columns}
    column_by_ordering = {c.ordering: c for c in columns}
    print(f"AFTER COLUMNS PRELOAD: {len(connection.queries) - initial_queries} new queries")

    # 2. PRELOAD ALL REPORT ITEMS (bitta query)
    report_items = list(ReportItem.objects.filter(report=report))
    item_by_column_id = {item.statement_column_id: item for item in report_items}
    print(f"AFTER REPORT ITEMS PRELOAD: {len(connection.queries) - initial_queries} new queries")

    item_ordering_map = {
        item.id: column_by_id[item.statement_column_id].ordering
        for item in report_items
    }

    # 3. PRELOAD ALL INNERS (bitta query). Use only() to avoid FK loads.
    inners = (
        ReportItemInner.objects
        .only("id", "report_item_id", "plant_id", "value")
        .filter(
            report_item__report=report,
            plant__isnull=False,
        )
    )
    inners = list(inners)
    print(f"AFTER INNERS PRELOAD: {len(connection.queries) - initial_queries} new queries")

    # Aggregate values
    values = defaultdict(lambda: defaultdict(Decimal))
    inner_map = {}


    for inner in inners:
        ordering = item_ordering_map[inner.report_item_id]
        plant_id = inner.plant_id
        val = normalize(inner.value)
        values[ordering][plant_id] += val
        inner_map[(ordering, plant_id)] = inner
    print(f"AFTER AGGREGATION LOOP: {len(connection.queries) - initial_queries} new queries")  # Bu yerda 0 bo'lishi kerak

    # Helpers...
    def get_sum(orderings: list[str], plant_id) -> Decimal:
        total = Decimal("0")
        for o in orderings:
            total += values[o][plant_id]
        return total


    new_items: list[ReportItem] = []
    # Collect pending inners as tuples to avoid ORM FK deref before IDs exist
    pending_inners: list[tuple] = []  # (statement_column_id, plant_id, value_str)
    update_inners: list[ReportItemInner] = []

    update_inners_map = {}
    pending_inner_keys = set()

    def set_value(ordering: str, plant_id, value: Decimal):
        # Use only precomputed maps and *_id fields; no ORM dereferencing.
        column = column_by_ordering.get(ordering)
        if not column:
            return

        value = value.quantize(Decimal("1.00"))

        item = item_by_column_id.get(column.id)
        if not item:
            # Create unsaved item; IDs will be assigned after bulk_create
            item = ReportItem(report=report, statement_column=column)
            item_by_column_id[column.id] = item
            new_items.append(item)

        key = (ordering, plant_id)
        existing_inner = inner_map.get(key)

        if existing_inner:
            if normalize(existing_inner.value) != value:
                existing_inner.value = str(value)
                update_inners_map[existing_inner.id] = existing_inner
        else:
            if key not in pending_inner_keys:
                pending_inners.append((column.id, plant_id, str(value)))
                pending_inner_keys.add(key)
            # Mark presence to avoid duplicates in same run
            inner_map[key] = None

        # Keep cache consistent for later formulas
        values[ordering][plant_id] = value

    # 6. CALCULATION LOGIC
    ordering_map = {
        "1.3.1.2": ["1.3.2.1.2", "1.3.2.2.2", "1.3.2.3.2"],
        "1.4.1.2": ["1.4.2.1.2", "1.4.2.2.2", "1.4.2.3.2"],
        "1.5.1.2": ["1.5.2.1.2", "1.5.2.2.2", "1.5.2.3.2"],
        "1.6.1.2": ["1.6.2.1.2", "1.6.2.2.2", "1.6.2.3.2"],
    }

    all_plant_ids = set()
    for plant_dict in values.values():
        all_plant_ids.update(plant_dict.keys())

    for plant_id in all_plant_ids:
        for chorak, months in ordering_map.items():
            amalda = get_sum(months, plant_id)
            set_value(chorak, plant_id, amalda)

            reja_ordering = chorak.replace(".2", ".1")
            farq_ordering = chorak.replace(".2", ".3")

            reja = get_sum([reja_ordering], plant_id)
            set_value(farq_ordering, plant_id, amalda - reja)

        yil_amalda = get_sum(list(ordering_map.keys()), plant_id)
        set_value("1.1.3", plant_id, yil_amalda)

        yil_reja = get_sum(["1.1.2"], plant_id)
        set_value("1.1.4", plant_id, yil_amalda - yil_reja)

        if yil_reja > 0:
            foiz = round_decimal((yil_amalda / yil_reja) * Decimal("100"), 1)
        else:
            foiz = Decimal("0")
        set_value("1.1.5", plant_id, foiz)
    print(f"AFTER CALCULATION LOOP: {len(connection.queries) - initial_queries} new queries")  # Bu yerda ham 0 bo'lishi kerak

    # 7. BULK SAVE
    #    Two-phase save to ensure FK integrity without extra queries.
    if new_items:
        ReportItem.objects.bulk_create(new_items)

    if pending_inners:
        # Build ORM objects using only IDs; avoids any FK dereferencing.
        build_inners = []
        for statement_column_id, plant_id, value_str in pending_inners:
            item = item_by_column_id[statement_column_id]
            build_inners.append(
                ReportItemInner(
                    report_item_id=item.id,
                    plant_id=plant_id,
                    value=value_str,
                )
            )
        if build_inners:
            ReportItemInner.objects.bulk_create(build_inners)

    if update_inners_map:
        ReportItemInner.objects.bulk_update(
            list(update_inners_map.values()), ["value"]
        )
    print(f"END: Total new queries: {len(connection.queries) - initial_queries}")
