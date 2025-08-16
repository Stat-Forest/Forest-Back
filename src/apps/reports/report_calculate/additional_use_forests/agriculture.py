from decimal import Decimal
from apps.reports.models import ReportItem, Report, ReportItemInner


def calculate_qishloq_xojaligi(report: Report):
    """
    Qishloq xo‘jaligi ilovalari hisoblash:
    Har bir blok (ilova) o‘zidagi ekinlar summasini umumiy ustunga qo‘shadi.
    """

    columns = report.statement.columns.select_related("parent").all()

    # ==================== Moyli ilovasi ====================
    calculate_ilova(
        columns=columns,
        report=report,
        parent_ordering="1.1.2",
        crop_orderings=["1.1.3.1", "1.1.3.2", "1.1.3.3", "1.1.3.4", "1.1.3.5"]
    )

    # ==================== Bodom va Pista ilovasi ====================
    calculate_ilova(
        columns=columns,
        report=report,
        parent_ordering="1.1.2",  # Jami yong‘oqmevalilar
        crop_orderings=["1.1.3.1", "1.1.3.2", "1.1.3.3"]  # Grek, Bodom, Pista
    )


def calculate_ilova(columns, report, parent_ordering, crop_orderings):
    """
    Har qanday ekin ilovasini hisoblab, natijani parent ustunlarga joylaydi.
    """

    suffix_map = {"1": "ga", "2": "s/ga", "3": "tn"}
    result = {"ga": Decimal(0), "s/ga": Decimal(0), "tn": Decimal(0)}

    parent_cols = {
        suffix_map.get(col.ordering.rsplit(".", 1)[-1]): col
        for col in columns
        if col.parent and col.parent.ordering == parent_ordering
    }

    # 🔽 Oldindan barcha itemlarni olish va dictga solish
    report_items_map = {
        item.statement_column_id: item
        for item in report.report_items.prefetch_related("inners").all()
    }

    for col in columns:
        if col.parent and col.parent.ordering in crop_orderings:
            suffix = col.ordering.rsplit(".", 1)[-1]
            key = suffix_map.get(suffix)
            if key:
                item = report_items_map.get(col.id)
                if item and item.inners.exists():
                    result[key] += Decimal(item.inners.first().value or 0)

    for key, value in result.items():
        if key in parent_cols:
            item = ReportItem.objects.create(report=report, statement_column=parent_cols[key])
            ReportItemInner.objects.create(report_item=item, value=str(value))

    # Barcha ustunlar
    # columns = report.statement.columns.prefetch_related("parent").all()
    #
    # # Moyli ekinlar bo‘limining 3ta ustunini aniqlaymiz
    # moyli_columns = {
    #     col.title_uz: col
    #     for col in columns
    #     if col.parent and col.parent.title_uz == "Moyli ekinlar"
    # }
    #
    # # Har bir mahsulotning ustunlarini guruhlab olish
    # crops = ["Mashar", "Kunjut", "Yer yong'oq", "Kungaboqar", "Zig'ir"]
    # crop_columns = {crop: {} for crop in crops}
    #
    # for col in columns:
    #     if col.parent and col.parent.title_uz in crops:
    #         crop_columns[col.parent.title_uz][col.title_uz] = col
    #
    # # Summalarni boshlash
    # result = {"ga": Decimal(0), "s/ga": Decimal(0), "tn": Decimal(0)}
    #
    # # Har bir mahsulotni aylantirib yig‘amiz
    # for crop in crops:
    #     for unit in ["ga", "s/ga", "tn"]:
    #         col = crop_columns[crop].get(unit)
    #         if not col:
    #             continue
    #         item = report.report_items.filter(statement_column=col).first()
    #         if item:
    #             value = item.inners.first().value
    #             result[unit] += Decimal(str(value or 0))
    #
    # # Natijani umumiy Moyli ekinlar ustunlariga yozamiz
    # for unit in ["ga", "s/ga", "tn"]:
    #     col = moyli_columns.get(unit)
    #     if col:
    #         item = ReportItem.objects.create(
    #             report=report,
    #             statement_column=col
    #         )
    #         ReportItemInner.objects.create(
    #             report_item=item,
    #             value=str(result[unit])
    #         )
