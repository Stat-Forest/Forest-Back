from collections import defaultdict
from decimal import Decimal
from apps.reports.models import Report, ReportItem, ReportItemInner
from apps.reports.report_calculate.forest_create.forest_create_statement import create_calculated_items


def calculate_seed_movement(report: Report):
    ordering_map = {
        "REJA": "1.1.2.1",
        "AMALDA": "1.1.2.2",
        "FOIZ": "1.1.2.3",

        "YIL_BOSHIGA_QOLDIQ": "1.1.3",

        "XOJALIK_JAMI": "1.1.4.1.1.1",
        "XOJALIK_UCHASTKA": "1.1.4.1.1.2",
        "BOSHQADAN_OLINDI": "1.1.4.1.2.1",
        "JAMI_TAYYORLANDI": "1.1.4.1",

        "SARFLANDI_JAMI": "1.1.5.1",
        "SARFLANDI_KG_LIST": [
            "1.1.5.1.1.1",
            "1.1.5.1.2.1",
            "1.1.5.1.3.1",
            "1.1.5.1.4.1",
            "1.1.5.1.5.1",
        ],

        "OXIRGI_QOLDIQ": "1.1.6",
    }

    # Step 1: Barcha kerakli columnlar va ularning orderinglarini yig‘ib olamiz
    all_orderings = set()
    for val in ordering_map.values():
        if isinstance(val, list):
            all_orderings.update(val)
        else:
            all_orderings.add(val)

    all_columns = report.statement.columns.prefetch_related("children").all()
    columns_by_ordering = {col.ordering: col for col in all_columns if col.ordering in all_orderings}

    # Step 2: Kerakli report item innerlarini oldindan olish
    items = ReportItem.objects.filter(
        report=report,
        statement_column__ordering__in=all_orderings
    ).select_related("statement_column")

    item_inners = ReportItemInner.objects.filter(
        report_item__in=items
    ).select_related("report_item", "report_item__statement_column")

    # Step 3: Innerlarni ordering bo‘yicha guruhlab olamiz
    inner_map = defaultdict(list)
    for inner in item_inners:
        ordering = inner.report_item.statement_column.ordering
        try:
            inner_map[ordering].append(Decimal(inner.value))
        except (ValueError, TypeError):
            continue

    # Step 4: Foydali funksiya
    def get_value(ordering: str | list[str]) -> Decimal:
        if isinstance(ordering, str):
            return sum(inner_map[ordering])
        return sum(sum(inner_map[o]) for o in ordering if o in inner_map)

    # Hisoblashlar
    reja = get_value(ordering_map["REJA"])
    amalda = get_value(ordering_map["AMALDA"])
    foiz = (amalda / reja * 100) if reja else Decimal(0)
    create_calculated_items(report, columns_by_ordering.get(ordering_map["FOIZ"]), foiz)

    tayyorlangan_jami = (
            get_value(ordering_map["XOJALIK_JAMI"]) +
            get_value(ordering_map["XOJALIK_UCHASTKA"]) +
            get_value(ordering_map["BOSHQADAN_OLINDI"])
    )
    create_calculated_items(report, columns_by_ordering.get(ordering_map["JAMI_TAYYORLANDI"]), tayyorlangan_jami)

    sarflangan_jami = get_value(ordering_map["SARFLANDI_KG_LIST"])
    create_calculated_items(report, columns_by_ordering.get(ordering_map["SARFLANDI_JAMI"]), sarflangan_jami)

    oxirgi_qoldiq = (
            get_value(ordering_map["YIL_BOSHIGA_QOLDIQ"]) +
            tayyorlangan_jami +
            sarflangan_jami
    )
    create_calculated_items(report, columns_by_ordering.get(ordering_map["OXIRGI_QOLDIQ"]), oxirgi_qoldiq)
