from decimal import Decimal
from collections import defaultdict

from apps.reports.models import Report, ReportItem, ReportItemInner
from apps.reports.report_calculate.forest_create.forest_create_statement import create_calculated_items


def calculate_make_pencil(report: Report):
    """
    4-ilova: Qalamchalar tayyorlash bo‘limi hisoboti
    Daraxt turlarining "Amalda" qiymatlari yig‘ilib, umumiy Amalda ustuniga yoziladi.
    Reja ustuniga nisbatan Foiz hisoblanadi.
    """

    # Orderinglar
    jami_reja_ordering = "1.1.2.1"
    jami_amalda_ordering = "1.1.2.2"
    jami_foiz_ordering = "1.1.2.3"
    tree_base_orderings = [
        "1.1.3.1.2",  # Terak Amalda
        "1.1.3.2.2",  # Jiyda Amalda
        "1.1.3.3.2",  # Chinar Amalda
        "1.1.3.4.2",  # Majnutol Amalda
        "1.1.3.5.2",  # Tol Amalda
        "1.1.3.6.2",  # Xilokatalpa Amalda
        "1.1.3.7.2",  # Boshqa turlar Amalda
    ]

    all_needed_orderings = [jami_reja_ordering, jami_foiz_ordering, jami_amalda_ordering] + tree_base_orderings

    # Barcha kerakli columnlarni topamiz
    columns = report.statement.columns.prefetch_related("children").all()
    column_map = {col.ordering: col for col in columns if col.ordering in all_needed_orderings}

    # Barcha kerakli item va innerlar
    items = ReportItem.objects.filter(
        report=report,
        statement_column__ordering__in=all_needed_orderings
    ).select_related("statement_column")
    inners = ReportItemInner.objects.filter(report_item__in=items).select_related(
        "report_item", "report_item__statement_column"
    )

    # Qiymatlarni ordering bo‘yicha to‘plash
    inner_map = defaultdict(list)
    for inner in inners:
        ordering = inner.report_item.statement_column.ordering
        try:
            inner_map[ordering].append(Decimal(inner.value))
        except (ValueError, TypeError):
            continue

    def get_value(ordering: str) -> Decimal:
        return sum(inner_map[ordering]) if ordering in inner_map else Decimal(0)

    # Amalda jami
    total_amalda = sum(get_value(ordering) for ordering in tree_base_orderings)
    create_calculated_items(report, column_map.get(jami_amalda_ordering), total_amalda)

    # Foiz hisoblash
    reja = get_value(jami_reja_ordering)
    foiz = (total_amalda / reja * 100) if reja else Decimal(0)
    create_calculated_items(report, column_map.get(jami_foiz_ordering), foiz)
