from decimal import Decimal, InvalidOperation

from apps.reports.models import Report, ReportItem, ReportItemInner
from apps.reports.services.get_two_numbers_in_percent import round_decimal


def safe_decimal(val):
    try:
        return Decimal(str(val)) if val is not None else Decimal(0)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(0)


def calculate_make_pencil(report: Report):
    """
    4-ilova: Qalamchalar tayyorlash bo‘limi hisoboti
    1.1.2.2 = 1.1.3.1 + ... + 1.1.3.10
    1.1.2.3 = (1.1.2.2 / 1.1.2.1) * 100
    """

    ordering_reja = "1.1.2.1"
    ordering_amalda = "1.1.2.2"
    ordering_foiz = "1.1.2.3"
    tree_orderings = [f"1.1.3.{i}" for i in range(1, 11)]

    all_orderings = [ordering_reja, ordering_amalda, ordering_foiz] + tree_orderings

    # Barcha kerakli StatementColumn lar
    columns = {
        col.ordering: col for col in report.statement.columns.filter(ordering__in=all_orderings)
    }

    # Barcha mavjud ReportItem lar va ularning innerlari
    report_items = (
        ReportItem.objects
        .filter(report=report, statement_column__ordering__in=all_orderings)
        .select_related("statement_column")
        .prefetch_related("inners")
    )
    item_map = {item.statement_column.ordering: item for item in report_items}

    # Qiymatlarni olish uchun yordamchi
    def get_value(ordering: str) -> Decimal:
        item = item_map.get(ordering)
        if not item:
            return Decimal(0)
        return sum(safe_decimal(inner.value) for inner in item.inners.all())

    # Amalda = daraxt turlarining jami
    total_amalda = sum(get_value(ordering) for ordering in tree_orderings)

    # Reja
    total_reja = get_value(ordering_reja)

    # Foiz = (Amalda / Reja) * 100
    total_foiz = (total_amalda / total_reja * 100) if total_reja else Decimal(0)

    total_foiz = round_decimal(total_foiz, 2)

    # Yozib qo‘yamiz
    def save_to_report(ordering: str, value: Decimal):
        column = columns.get(ordering)
        if not column:
            return

        item = item_map.get(ordering)
        if not item:
            item = ReportItem.objects.create(report=report, statement_column=column)
            item_map[ordering] = item

        ReportItemInner.objects.update_or_create(
            report_item=item,
            defaults={"value": str(value)}
        )

    save_to_report(ordering_amalda, total_amalda)
    save_to_report(ordering_foiz, total_foiz)
