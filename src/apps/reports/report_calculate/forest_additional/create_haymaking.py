from apps.reports.models import Report, ReportItem, ReportItemInner
from decimal import Decimal


def normalize(value):
    try:
        return Decimal(str(value))
    except:
        return Decimal(0)

def sum_values(report_items, ordering):
    for item in report_items:
        if item.statement_column.ordering == ordering:
            total = sum(
                normalize(inner.value)
                for inner in item.inners.all()
            )
            return total
    return Decimal(0)


def calculate_haymaking(report: Report):
    """
    Pichan o‘rish bo‘limi:
    Qolgan qismi = Berilgan ruxsatnoma summasi (1.1.8) - To‘langan summa (1.1.9)
    """

    statement = report.statement
    columns = statement.columns.prefetch_related("children").all()
    col_map = {col.ordering: col for col in columns}

    report_items = report.report_items.prefetch_related("inners", "statement_column")

    ruxsatnoma = sum_values(report_items, "1.1.8")
    tolangan = sum_values(report_items, "1.1.9")
    qolgan = ruxsatnoma - tolangan

    # Qolgan ustun 1.1.10
    create_calculated_item(report, col_map["1.1.10"], qolgan)


def create_calculated_item(report, column, value):
    item = ReportItem.objects.create(
        report=report,
        statement_column=column
    )
    ReportItemInner.objects.create(
        report_item=item,
        value=str(value)
    )