from decimal import Decimal
from apps.reports.models import ReportItem, Report, ReportItemInner
from apps.reports.report_calculate.additional_use_forests.k_x_svod import calculate_kxsvod


def calculate_qishloq_xojaligi(report: Report):
    """
    Qishloq xo‘jaligi ilovalari hisoblash:
    Har bir blok (ilova) o‘zidagi ekinlar summasini umumiy ustunga qo‘shadi.
    """

    columns = report.statement.columns.select_related("parent").all()

    # ==================== Moyli ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="4.1.2",  # Moyli ekinlar jami
        crop_orderings=["4.1.3.1", "4.1.3.2", "4.1.3.3", "4.1.3.4", "4.1.3.5"]
    )

    # ==================== Bodom va Pista ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="8.1.2",  # Jami yong‘oqmevalilar
        crop_orderings=["8.1.3.1", "8.1.3.2", "8.1.3.3"]
    )

    # ==================== Boshoqli Don ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="1.1.2",
        crop_orderings=["1.1.4.1", "1.1.4.2", "1.1.4.3", "1.1.4.4", "1.1.4.5", "1.1.4.6"]
    )

    # ==================== Sabzavot ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="2.1.2",
        crop_orderings=[
            "2.1.3.1", "2.1.3.2", "2.1.3.3", "2.1.3.4", "2.1.3.5", "2.1.3.6",
            "2.1.3.7", "2.1.3.8", "2.1.3.9", "2.1.3.10", "2.1.3.11", "2.1.3.12"
        ]
    )

    # ==================== Poliz ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="3.1.2",
        crop_orderings=[
            "3.1.3.1", "3.1.3.2", "3.1.3.3"
        ]
    )

    # ==================== Dukkakli ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="5.1.2",
        crop_orderings=[
            "5.1.3.1", "5.1.3.2", "5.1.3.3", "5.1.3.4"
        ]
    )

    # ==================== Ozuqa ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="6.1.2",
        crop_orderings=[
            "6.1.3.1", "6.1.3.2", "6.1.3.3", "6.1.3.4"
        ]
    )

    # ==================== Bog` Tok ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="7.1.2",
        crop_orderings=[
            "7.1.3.1", "7.1.3.2", "7.1.3.3"
        ]
    )
    # ==================== K-X SVOD(9-ilova) ====================
    calculate_kxsvod(report, columns)

def calculate_ilova(report, columns, parent_ordering: str, crop_orderings: list[str]):
    """
    Har qanday ilovani hisoblab, Jami ustunlariga qiymatlarni yozadi.
    """
    suffix_map = {"1": "ga", "2": "s/ga", "3": "tn", "4": "tn"}
    result = {"ga": Decimal(0), "s/ga": Decimal(0), "tn": Decimal(0)}

    # 1. Jami ustunlarni topamiz
    parent_cols = {
        suffix_map.get(col.ordering.rsplit(".", 1)[-1]): col
        for col in columns
        if col.parent and col.parent.ordering == parent_ordering
    }

    # 2. Oldindan barcha itemlarni olish
    report_items_map = {
        item.statement_column_id: item
        for item in report.report_items.prefetch_related("inners").all()
    }

    # 3. Mahsulotlarni yig‘amiz
    for col in columns:
        if any(col.ordering.startswith(order) for order in crop_orderings):
            suffix = col.ordering.rsplit(".", 1)[-1]
            key = suffix_map.get(suffix)
            if key:
                item = report_items_map.get(col.id)
                if item and item.inners.exists():
                    try:
                        result[key] += Decimal(item.inners.first().value or 0)
                    except:
                        continue

    # 4. Jami ustunlarga qiymat yozamiz
    for key, value in result.items():
        if key in parent_cols:
            parent_col = parent_cols[key]
            item, _ = ReportItem.objects.get_or_create(
                report=report,
                statement_column=parent_col
            )
            inner = item.inners.first()
            if inner:
                inner.value = str(value)
                inner.save(update_fields=["value"])
            else:
                ReportItemInner.objects.create(report_item=item, value=str(value))