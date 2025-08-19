from decimal import Decimal
from collections import defaultdict
from apps.reports.models import ReportItem, ReportItemInner, StatementColumn
from apps.utils.report_math import sum_values_analysis


def upsert_calculated_item(report, column, value):
    item, _ = ReportItem.objects.get_or_create(
        report=report,
        statement_column=column
    )
    inner = item.inners.first()
    if inner:
        inner.value = str(value)
        inner.save(update_fields=["value"])
    else:
        ReportItemInner.objects.create(
            report_item=item,
            value=str(value)
        )


def get_column_by_ordering(columns: list[StatementColumn], ordering: str):
    for col in columns:
        if col.ordering == ordering:
            return col
    return None


def sum_from_orderings(report, report_items_by_column_id, columns, parent_ordering: str, child_orderings: list[str]):
    parent_col = get_column_by_ordering(columns, parent_ordering)
    if not parent_col:
        return

    total = Decimal(0)
    for ordering in child_orderings:
        col = get_column_by_ordering(columns, ordering)
        if col:
            total += Decimal(sum_values_analysis(report_items_by_column_id, col))

    upsert_calculated_item(report, parent_col, total)


def calculate_employee_analysis(report):
    statement = report.statement
    columns = list(statement.columns.prefetch_related("children").all())

    # ✅ Barcha ReportItemlarni va innerlarini oldindan olib kelamiz
    all_items = ReportItem.objects.filter(report=report).select_related("statement_column").prefetch_related("inners")

    # ✅ report_items_by_column_id kesh tayyorlash
    report_items_by_column_id = defaultdict(list)
    for item in all_items:
        report_items_by_column_id[item.statement_column_id].append(item)

    # 🔢 1. Umumiy to‘plamlar
    sum_from_orderings(
        report,
        report_items_by_column_id,
        columns,
        parent_ordering="2.1.3.5.1",
        child_orderings=[
            "2.1.3.5.2.1", "2.1.3.5.2.2", "2.1.3.5.2.3", "2.1.3.5.2.4", "2.1.3.5.2.5"
        ]
    )

    # 🔢 2. Kasallik turlari
    sum_from_orderings(
        report,
        report_items_by_column_id,
        columns,
        parent_ordering="2.1.3.8.1",
        child_orderings=[
            "2.1.3.8.2.1", "2.1.3.8.2.2", "2.1.3.8.2.3"
        ]
    )

    # 🔢 3. Madaniy-ma’rifiy tadbirlar
    sum_from_orderings(
        report,
        report_items_by_column_id,
        columns,
        parent_ordering="2.1.3.10.1",
        child_orderings=[
            "2.1.3.10.2.1", "2.1.3.10.2.2", "2.1.3.10.2.3", "2.1.3.10.2.4"
        ]
    )

    # 🔢 4. Ilova-3 — Hisoblash
    col_oliy_jami = get_column_by_ordering(columns, "3.1.2.2.1.1")
    col_orta_maxsus_jami = get_column_by_ordering(columns, "3.1.2.2.2.1")
    col_orta = get_column_by_ordering(columns, "3.1.2.2.3")
    col_jami_target = get_column_by_ordering(columns, "3.1.2.1")

    if col_jami_target:
        total = Decimal(0)
        for col in [col_oliy_jami, col_orta_maxsus_jami, col_orta]:
            if col:
                total += Decimal(sum_values_analysis(report_items_by_column_id, col))
        upsert_calculated_item(report, col_jami_target, total)

    # 🔢 5. Yillik bo‘yicha
    year_orderings = [
        "3.1.6.2.1.1", "3.1.6.2.1.2", "3.1.6.2.1.3",
        "3.1.6.2.2.1", "3.1.6.2.2.2", "3.1.6.2.2.3",
        "3.1.6.2.3.1", "3.1.6.2.3.2", "3.1.6.2.3.3"
    ]
    col_jami_years = get_column_by_ordering(columns, "3.1.6.1")
    if col_jami_years:
        total = Decimal(0)
        for ordering in year_orderings:
            col = get_column_by_ordering(columns, ordering)
            if col:
                total += Decimal(sum_values_analysis(report_items_by_column_id, col))
        upsert_calculated_item(report, col_jami_years, total)
