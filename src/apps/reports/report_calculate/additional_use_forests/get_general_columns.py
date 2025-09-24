from apps.reports.mapping_columns import ORDERING_MAP


def calculate_kx_svod_from_8_app(report, columns):
    from apps.reports.models import ReportItem, ReportItemInner

    report_items = (
        ReportItem.objects
        .filter(report=report)
        .select_related("statement_column")
    )

    inners = (
        ReportItemInner.objects
        .filter(report_item__report=report)
        .select_related("report_item")
    )

    # === STEP 1: Create mapping ===
    report_item_map = {
        item.statement_column.ordering: item
        for item in report_items
        if item.statement_column and item.statement_column.ordering
    }

    # Optimized mapping of inners
    inner_map = {}
    for inner in inners:
        rid = inner.report_item_id
        if rid not in inner_map:
            inner_map[rid] = []
        inner_map[rid].append(inner)

    # Columns mapping
    all_ordering = set(ORDERING_MAP.keys()) | set(ORDERING_MAP.values()) | {"9.1.1"}
    statement_columns = {
        col.ordering: col for col in columns if col.ordering in all_ordering
    }

    # === STEP 2: Delete old 9.1.* columns ===
    kx_svod_columns = [col for col in columns if col.ordering.startswith("9.")]
    ReportItem.objects.filter(report=report, statement_column__in=kx_svod_columns).delete()

    # === STEP 3: Copy data from 8 ilova → 9-ilova ===
    new_items = []
    new_inners = []

    for from_ordering, to_ordering in ORDERING_MAP.items():
        source_item = report_item_map.get(from_ordering)
        if not source_item:
            continue

        target_column = statement_columns.get(to_ordering)
        if not target_column:
            continue

        source_inners = inner_map.get(source_item.id)
        if not source_inners:
            continue

        new_item = ReportItem(
            report=report,
            statement_column=target_column
        )
        new_items.append(new_item)

        new_inners.append(
            ReportItemInner(
                value=source_inners[0].value,
                report_item=new_item
            )
        )

    # === STEP 4: Add Tashkilot Nomi (9.1.1) ===
    org_column = statement_columns.get("9.1.1")
    if org_column and report.organization and report.organization.name:
        org_item = ReportItem(
            report=report,
            statement_column=org_column
        )
        new_items.append(org_item)
        new_inners.append(
            ReportItemInner(
                value=report.organization.name,
                report_item=org_item
            )
        )

    # === STEP 5: Save new objects efficiently ===
    ReportItem.objects.bulk_create(new_items)
    ReportItemInner.objects.bulk_create(new_inners)
