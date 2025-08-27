from decimal import Decimal
from collections import defaultdict

from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn


def calculate_pasture(report: Report):
    """
    Yaylov hisoboti uchun ustunlarni hisoblaydi:
    - 1.1.7: Chorva jami soni
    - 1.1.9: Shartnoma summasi
    - 1.1.11: Qolgan qismi
    """

    required_orderings = [
        "1.1.7", "1.1.9", "1.1.10", "1.1.11",
        "1.1.8.1", "1.1.8.2", "1.1.8.4", "1.1.8.6", "1.1.8.7", "1.1.8.8", "1.1.8.10",  # chorva soni
        "1.1.8.3", "1.1.8.5", "1.1.8.9", "1.1.8.11",  # summalar
    ]

    columns = report.statement.columns.filter(ordering__in=required_orderings)
    col_map = {col.ordering: col for col in columns}

    # --- KESH: Barcha qiymatlarni oldindan olish
    all_inners = ReportItemInner.objects.filter(
        report_item__report=report
    ).select_related("report_item", "report_item__statement_column")

    inner_values = defaultdict(list)  # col_id -> [values]
    for inner in all_inners:
        col_id = inner.report_item.statement_column_id
        inner_values[col_id].append(inner.value)

    # --- Yordamchi funksiyalar (cached ishlaydi)
    def sum_values(col_list: list[StatementColumn]) -> Decimal:
        total = Decimal(0)
        for col in col_list:
            for val in inner_values.get(col.id, []):
                try:
                    total += Decimal(str(val))
                except:
                    continue
        return total

    def create_calculated_items(column: StatementColumn, value: Decimal):
        item = ReportItem.objects.create(report=report, statement_column=column)
        ReportItemInner.objects.create(report_item=item, value=str(value))

    # --- 1. Chorva jami soni (1.1.7)
    chorva_soni_cols = [col_map[o] for o in ["1.1.8.1", "1.1.8.2", "1.1.8.4", "1.1.8.6", "1.1.8.7", "1.1.8.8", "1.1.8.10"]]
    chorva_total = sum_values(chorva_soni_cols)
    create_calculated_items(col_map["1.1.7"], chorva_total)

    # --- 2. Shartnoma summasi (1.1.9)
    summasi_cols = [col_map[o] for o in ["1.1.8.3", "1.1.8.5", "1.1.8.9", "1.1.8.11"]]
    shartnoma_total = sum_values(summasi_cols)
    create_calculated_items(col_map["1.1.9"], shartnoma_total)

    # --- 3. Qolgan qismi (1.1.11) = 1.1.9 - 1.1.10
    tolangan = sum_values([col_map["1.1.10"]])
    qoldiq = shartnoma_total - tolangan
    create_calculated_items(col_map["1.1.11"], qoldiq)
