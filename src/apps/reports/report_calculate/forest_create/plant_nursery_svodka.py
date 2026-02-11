import uuid
from decimal import Decimal, InvalidOperation
from django.db.models import Prefetch
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
    # 1. BARCHA KERAKLI COLUMNLARNI BIR QUERYDA OLISH (ID BO'YICHA CACHE)
    # ===============================
    # Avval statementdagi barcha columnlarni olamiz
    all_columns = StatementColumn.objects.filter(statement=report.statement)

    # Ordering bo'yicha ham cache qilamiz (keyingi ishlatish uchun)
    columns_by_ordering = {c.ordering: c for c in all_columns}

    # Kerakli orderinglar
    needed_orderings = {
        "3.1.7.1.2.1", "3.1.7.1.2.2",  # source orderings
        "1.1.3.1.2", "1.1.3.2.2", "1.1.3.1.1", "1.1.3.1.3",
        "1.1.3.2.1", "1.1.3.2.3", "1.1.2.1", "1.1.2.2", "1.1.2.3"
    }

    # Faqat kerakli columnlarni olish
    columns = {ordering: columns_by_ordering.get(ordering) for ordering in needed_orderings}

    # ===============================
    # 2. TARGET REPORT ITEMLARINI BIR QUERYDA OLISH (inners bilan)
    # ===============================
    # Avval report items va ularning innerlarini bitta complex queryda olamiz
    report_items_qs = ReportItem.objects.filter(
        report=report
    ).select_related('statement_column').prefetch_related(
        Prefetch('inners', queryset=ReportItemInner.objects.all(), to_attr='inner_list')
    )

    # Dictionarylarni tayyorlaymiz
    items_by_ordering = {}
    inners_by_ordering = {}

    # StatementColumn ID larini orderinglarga aylantiramiz
    for item in report_items_qs:
        if item.statement_column:
            ordering = item.statement_column.ordering
            items_by_ordering[ordering] = item

            if hasattr(item, 'inner_list') and item.inner_list:
                inners_by_ordering[ordering] = item.inner_list[0]
            else:
                inners_by_ordering[ordering] = None

    # ===============================
    # 3. SOURCE REPORT ITEMLARINI BIR QUERYDA OLISH (optimized)
    # ===============================
    SOURCE_TO_TARGET = {
        "3.1.7.1.2.1": "1.1.3.1.2",
        "3.1.7.1.2.2": "1.1.3.2.2",
    }

    source_orderings = list(SOURCE_TO_TARGET.keys())

    # Source report uchun ham bitta query
    source_items_qs = ReportItem.objects.filter(
        report=source_report,
        statement_column__ordering__in=source_orderings
    ).select_related('statement_column').prefetch_related(
        Prefetch('inners', queryset=ReportItemInner.objects.all(), to_attr='inner_list')
    )

    source_inners_map = {}
    for item in source_items_qs:
        if item.statement_column:
            ordering = item.statement_column.ordering
            if hasattr(item, 'inner_list') and item.inner_list:
                source_inners_map[ordering] = item.inner_list[0]

    # ===============================
    # 4. NEW/UPDATE OBJECTS COLLECTORS
    # ===============================
    new_items = {}
    new_inners = {}
    update_inners = []

    def get_val(ordering):
        inner = inners_by_ordering.get(ordering)
        return D(inner.value) if inner else Decimal("0")

    def set_val(ordering, value):
        column = columns.get(ordering)
        if not column:
            print(f"⚠️ Column not found for ordering: {ordering}")
            return

        item = items_by_ordering.get(ordering)

        if not item:
            # Yangi item yaratish
            item = ReportItem(
                id=uuid.uuid4(),
                report=report,
                statement_column=column
            )
            items_by_ordering[ordering] = item
            new_items[ordering] = item

            # Yangi inner yaratish
            inner = ReportItemInner(
                id=uuid.uuid4(),
                report_item=item,
                value=str(value)
            )
            new_inners[ordering] = inner
            inners_by_ordering[ordering] = inner
        else:
            # Mavjud itemni yangilash
            inner = inners_by_ordering.get(ordering)

            if inner:
                # Agar inner mavjud bo'lsa, qiymatni tekshirib yangilash
                if D(inner.value) != value:
                    inner.value = str(value)
                    update_inners.append(inner)
            else:
                # Yangi inner yaratish
                inner = ReportItemInner(
                    id=uuid.uuid4(),
                    report_item=item,
                    value=str(value)
                )
                new_inners[ordering] = inner
                inners_by_ordering[ordering] = inner

    # ===============================
    # 5. SOURCE → TARGET IMPORT
    # ===============================
    for src_ordering, target_ordering in SOURCE_TO_TARGET.items():
        if src_ordering in source_inners_map:
            set_val(target_ordering, D(source_inners_map[src_ordering].value))

    # ===============================
    # 6. CALCULATIONS
    # ===============================
    # 1.1.3.1.3 = (1.1.3.1.2 / 1.1.3.1.1) * 100
    set_val(
        "1.1.3.1.3",
        safe_percent(
            get_val("1.1.3.1.2"),
            get_val("1.1.3.1.1"),
        )
    )

    # 1.1.3.2.3 = (1.1.3.2.2 / 1.1.3.2.1) * 100
    set_val(
        "1.1.3.2.3",
        safe_percent(
            get_val("1.1.3.2.2"),
            get_val("1.1.3.2.1"),
        )
    )

    # 1.1.2.2 = 1.1.3.1.2 + 1.1.3.2.2
    jami_amalda = (
            get_val("1.1.3.1.2") +
            get_val("1.1.3.2.2")
    )
    set_val("1.1.2.2", jami_amalda)

    # 1.1.2.3 = (1.1.2.2 / 1.1.2.1) * 100
    set_val(
        "1.1.2.3",
        safe_percent(
            jami_amalda,
            get_val("1.1.2.1"),
        )
    )

    # ===============================
    # 7. BULK SAVE (optimized)
    # ===============================
    if new_items:
        ReportItem.objects.bulk_create(
            new_items.values(),
            batch_size=100
        )
        print(f"✅ Created {len(new_items)} new ReportItems")

    if new_inners:
        ReportItemInner.objects.bulk_create(
            new_inners.values(),
            batch_size=100
        )
        print(f"✅ Created {len(new_inners)} new ReportItemInners")

    if update_inners:
        ReportItemInner.objects.bulk_update(
            update_inners,
            ["value"],
            batch_size=100
        )
        print(f"✅ Updated {len(update_inners)} ReportItemInners")

    print(f"✅ calculate_kochat_nursery FINISHED — {len(new_items)} new, {len(update_inners)} updated")