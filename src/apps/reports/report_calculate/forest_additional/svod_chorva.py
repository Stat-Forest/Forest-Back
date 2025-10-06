from decimal import Decimal, InvalidOperation
from collections import defaultdict
from apps.reports.mapping_columns import SECOND_ORDERING_MAP


def calculate_svod_chorva(report):
    from apps.reports.models import ReportItemInner, StatementColumn, ReportItem

    """
    Svod Chorva hisobotining avtomatik ustunlarini hisoblaydi.
    """
    # === 1. Barcha mavjud innersni olamiz ===
    inners = ReportItemInner.objects.filter(
        report_item__report=report
    ).select_related("report_item__statement_column")

    # Guruhlab olamiz: ordering -> [Decimal values]
    grouped = defaultdict(list)
    for inner in inners:
        ordering = inner.report_item.statement_column.ordering
        raw_value = inner.value or "0"
        try:
            val = Decimal(str(raw_value).strip())
        except (TypeError, ValueError, InvalidOperation):
            val = Decimal(0)
        grouped[ordering].append(val)

    # === 2. SECOND_ORDERING_MAP dagi oddiy yig‘indilarni hisoblaymiz ===
    totals = {}  # key = ordering, value = Decimal
    for result_ordering, source_orderings in SECOND_ORDERING_MAP.items():
        total = Decimal(0)
        for ordering in source_orderings:
            values = grouped.get(ordering, [])
            total += sum(values) if values else Decimal(0)
        totals[result_ordering] = total

        try:
            target_column = StatementColumn.objects.get(
                ordering=result_ordering,
                statement=report.statement
            )
        except StatementColumn.DoesNotExist:
            continue

        report_item, _ = ReportItem.objects.get_or_create(
            report=report,
            statement_column=target_column
        )
        ReportItemInner.objects.update_or_create(
            report_item=report_item,
            defaults={"value": str(total)}
        )

    # === 3. Farqi va % ni qo‘lda hisoblaymiz ===
    try:
        col_farqi = StatementColumn.objects.get(ordering="7.1.5", statement=report.statement)
    except StatementColumn.DoesNotExist:
        col_farqi = None
    try:
        col_foiz = StatementColumn.objects.get(ordering="7.1.6", statement=report.statement)
    except StatementColumn.DoesNotExist:
        col_foiz = None

    # 7.1.2 (Reja) va 7.1.4 (Mavjud) qiymatlarini olamiz
    val_7_1_2 = totals.get("7.1.2", Decimal(0))
    val_7_1_4 = totals.get("7.1.4", Decimal(0))

    # Farqi = 7.1.2 - 7.1.4
    farqi = val_7_1_2 - val_7_1_4
    # % = (7.1.4 / 7.1.2) * 100
    foiz = (val_7_1_4 / val_7_1_2 * 100) if val_7_1_2 else Decimal(0)

    if col_farqi:
        item_farqi, _ = ReportItem.objects.get_or_create(
            report=report,
            statement_column=col_farqi
        )
        ReportItemInner.objects.update_or_create(
            report_item=item_farqi,
            defaults={"value": str(farqi)}
        )

    if col_foiz:
        item_foiz, _ = ReportItem.objects.get_or_create(
            report=report,
            statement_column=col_foiz
        )
        ReportItemInner.objects.update_or_create(
            report_item=item_foiz,
            defaults={"value": str(foiz)}
        )

    # === 4. Tashkilot nomini ham yozamiz (7.1.1) ===
    try:
        org_column = StatementColumn.objects.get(ordering="7.1.1", statement=report.statement)
    except StatementColumn.DoesNotExist:
        org_column = None

    if org_column and report.organization and report.organization.name:
        org_item, _ = ReportItem.objects.get_or_create(
            report=report,
            statement_column=org_column
        )
        ReportItemInner.objects.update_or_create(
            report_item=org_item,
            defaults={"value": report.organization.name}
        )