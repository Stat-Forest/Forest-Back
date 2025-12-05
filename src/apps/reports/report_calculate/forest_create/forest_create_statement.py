from decimal import Decimal, InvalidOperation

from apps.reports.models import Report, ReportItem, ReportItemInner
from apps.reports.services.get_two_numbers_in_percent import round_decimal


def normalize_decimal(value) -> Decimal:
    try:
        if value is None or value == "":
            return Decimal(0)
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(0)


def calculate_forest_statement(report: Report):
    ordering = {
        "JAMI_REJA": "1.1.2.1",
        "JAMI_AMALDA": "1.1.2.2",
        "JAMI_FOIZ": "1.1.2.3",

        "ODDIY_1_AMALDA": "1.1.3.2",
        "ODDIY_2_AMALDA": "1.1.4.2",

        "ODDIY_1_SRC": ["1.1.5.2", "1.1.6.2"],

        "YONGOQ_JAMI": "1.1.7",
        "YONGOQ_SRC": ["1.1.8.1", "1.1.8.2", "1.1.8.3"],

        "TEZ_OSUV_JAMI_AMALDA": "1.1.9.2",
        "TEZ_OSUV_JAMI_REJA": "1.1.9.1",
        "TEZ_OSUV_JAMI_FOIZ": "1.1.9.3",
        "TEZ_OSUV_SRC": [
            "1.1.10.1", "1.1.10.2", "1.1.10.3",
            "1.1.10.4", "1.1.10.5", "1.1.10.6", "1.1.10.7"
        ],

        "TABIIY_TIKLANISH": "1.1.11.2",
    }

    # --- load columns ---
    columns_by_ordering = {
        col.ordering: col for col in report.statement.columns.all()
    }

    # --- load existing values ---
    report_items = (
        ReportItem.objects.filter(report=report)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    existing_items = {}
    column_value_map = {}

    for item in report_items:
        ord_ = item.statement_column.ordering
        existing_items[ord_] = item
        total = sum(normalize_decimal(inner.value) for inner in item.inners.all())
        column_value_map[ord_] = total

    def get_sum(orderings):
        if isinstance(orderings, str):
            orderings = [orderings]
        return sum(column_value_map.get(o, Decimal(0)) for o in orderings)

    def save_value(ord_, value: Decimal):
        column = columns_by_ordering.get(ord_)
        if not column:
            return
        item = existing_items.get(ord_)

        if item:
            inner = item.inners.first()
            if inner:
                if Decimal(inner.value or 0) != value:
                    inner.value = str(value)
                    inner.save(update_fields=["value"])
            else:
                ReportItemInner.objects.create(report_item=item, value=str(value))
        else:
            new_item = ReportItem.objects.create(report=report, statement_column=column)
            ReportItemInner.objects.create(report_item=new_item, value=str(value))
            existing_items[ord_] = new_item

    # ------------------------------------------
    # 1) 1.1.3.2 = 1.1.5.2 + 1.1.6.2
    # ------------------------------------------
    oddiy_1 = get_sum(ordering["ODDIY_1_SRC"])
    save_value(ordering["ODDIY_1_AMALDA"], oddiy_1)

    # ------------------------------------------
    # 2) 1.1.7 = 1.1.8.1 + 1.1.8.2 + 1.1.8.3
    # ------------------------------------------
    yongoq = get_sum(ordering["YONGOQ_SRC"])
    save_value(ordering["YONGOQ_JAMI"], yongoq)

    # ------------------------------------------
    # 3) 1.1.9.2 = sum(1.1.10.x)
    # ------------------------------------------
    tez_osuv = get_sum(ordering["TEZ_OSUV_SRC"])
    save_value(ordering["TEZ_OSUV_JAMI_AMALDA"], tez_osuv)

    # 1.1.9.3 foiz = 1.1.9.2 / 1.1.9.1 * 100
    reja_tez = column_value_map.get(ordering["TEZ_OSUV_JAMI_REJA"], Decimal(0))
    foiz_tez = (tez_osuv / reja_tez * 100) if reja_tez else Decimal(0)
    foiz_tez = round_decimal(foiz_tez, 1)  # <-- YANGI
    save_value(ordering["TEZ_OSUV_JAMI_FOIZ"], foiz_tez)

    # ------------------------------------------
    # 4) 1.1.2.2 = 1.1.3.2 + 1.1.4.2 + 1.1.7 + 1.1.9.2 + 1.1.11.2
    # ------------------------------------------
    jami_amalda = (
        oddiy_1 +
        column_value_map.get(ordering["ODDIY_2_AMALDA"], Decimal(0)) +
        yongoq +
        tez_osuv +
        column_value_map.get(ordering["TABIIY_TIKLANISH"], Decimal(0))
    )
    save_value(ordering["JAMI_AMALDA"], jami_amalda)

    # ------------------------------------------
    # 5) 1.1.2.3 = 1.1.2.2 / 1.1.2.1 * 100
    # ------------------------------------------
    jami_reja = column_value_map.get(ordering["JAMI_REJA"], Decimal(0))
    jami_foiz = (jami_amalda / jami_reja * 100) if jami_reja else Decimal(0)
    jami_foiz = round_decimal(jami_foiz, 1)  # <-- YANGI
    save_value(ordering["JAMI_FOIZ"], jami_foiz)

