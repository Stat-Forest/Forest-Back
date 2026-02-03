import uuid
from decimal import Decimal, InvalidOperation
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn
from apps.reports.services.get_two_numbers_in_percent import round_decimal


def D(val):
    try:
        if val in (None, "", "0", 0):
            return Decimal("0")
        return Decimal(str(val))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def safe_percent(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return round_decimal((numerator / denominator) * Decimal("100"), places=1)


def calculate_kochat_nursery(report: Report):
    print(">>> ENTER calculate_kochat_nursery")

    source_report = report.source_report
    if not source_report:
        return

    # ===============================
    # 1. CACHE: STATEMENT COLUMNS
    # ===============================
    columns = {
        c.ordering: c
        for c in StatementColumn.objects.filter(
            statement=report.statement
        )
    }

    # ===============================
    # 2. CACHE: REPORT ITEMS + INNERS (no .first())
    # ===============================
    report_items = (
        ReportItem.objects
        .filter(report=report)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    items = {i.statement_column.ordering: i for i in report_items}
    # Build a map to the first inner using prefetched list to avoid extra SELECTs
    inners = {}
    for i in report_items:
        cached_list = list(i.inners.all())  # uses prefetch cache
        inners[i.statement_column.ordering] = cached_list[0] if cached_list else None

    new_items = {}
    new_inners = {}
    update_inners = []

    def get_val(ordering: str) -> Decimal:
        inner = inners.get(ordering)
        return D(inner.value) if inner else Decimal("0")

    def set_val(ordering: str, value: Decimal):
        column = columns.get(ordering)
        if not column:
            return

        item = items.get(ordering)
        if not item:
            # Pre-assign a UUID to avoid any need to read PKs back later
            item = ReportItem(id=uuid.uuid4(), report=report, statement_column=column)
            items[ordering] = item
            new_items[ordering] = item
            new_inners[ordering] = ReportItemInner(
                id=uuid.uuid4(),
                report_item=item,
                value=str(value)
            )
            return

        inner = inners.get(ordering)
        if inner:
            if D(inner.value) != value:
                inner.value = str(value)
                update_inners.append(inner)
        else:
            new_inners[ordering] = ReportItemInner(
                id=uuid.uuid4(),
                report_item=item,
                value=str(value)
            )
            # keep the cache in sync to avoid later lookups
            inners[ordering] = new_inners[ordering]

    # ===============================
    # 3. IMPORT AMALDA (FROM SOURCE)
    # ===============================
    SOURCE_TO_TARGET = {
        "3.1.7.1.2.1": "1.1.3.1.2",
        "3.1.7.1.2.2": "1.1.3.2.2",
    }

    source_inners = (
        ReportItemInner.objects
        .filter(
            report_item__report=source_report,
            report_item__statement_column__ordering__in=SOURCE_TO_TARGET
        )
        .select_related("report_item", "report_item__statement_column")
    )

    for inner in source_inners:
        tgt = SOURCE_TO_TARGET.get(
            inner.report_item.statement_column.ordering
        )
        if tgt:
            set_val(tgt, D(inner.value))

    # ===============================
    # 4. FORMULALAR
    # ===============================

    # Niholxona %
    set_val(
        "1.1.3.1.3",
        safe_percent(
            get_val("1.1.3.1.2"),
            get_val("1.1.3.1.1"),
        )
    )

    # Ko‘chatxona %
    set_val(
        "1.1.3.2.3",
        safe_percent(
            get_val("1.1.3.2.2"),
            get_val("1.1.3.2.1"),
        )
    )

    # Jami amalda
    jami_amalda = (
        get_val("1.1.3.1.2") +
        get_val("1.1.3.2.2")
    )
    set_val("1.1.2.2", jami_amalda)

    # Jami %
    set_val(
        "1.1.2.3",
        safe_percent(
            jami_amalda,
            get_val("1.1.2.1"),
        )
    )

    # ===============================
    # 5. BULK SAVE
    # ===============================
    if new_items:
        ReportItem.objects.bulk_create(new_items.values(), batch_size=1000)

    if new_inners:
        ReportItemInner.objects.bulk_create(new_inners.values(), batch_size=2000)

    if update_inners:
        ReportItemInner.objects.bulk_update(update_inners, ["value"], batch_size=2000)

    print("✅ calculate_kochat_nursery FINISHED (OPTIMIZED)")
