from collections import defaultdict
from decimal import Decimal
from apps.reports.models import Report, ReportItem, ReportItemInner


def calculate_seed_movement(report: Report):
    ordering_map = {
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

    # === ALL ORDERINGS
    all_orderings = set()
    for val in ordering_map.values():
        all_orderings.update(val if isinstance(val, list) else [val])

    # === Load statement columns
    columns = {
        col.ordering: col for col in
        report.statement.columns.filter(ordering__in=all_orderings)
    }

    # === Load existing items and their inners
    report_items = ReportItem.objects.filter(
        report=report,
        statement_column__ordering__in=all_orderings
    ).select_related("statement_column").prefetch_related("inners")

    item_map = {item.statement_column.ordering: item for item in report_items}

    inner_values = defaultdict(list)
    for item in report_items:
        ordering = item.statement_column.ordering
        for inner in item.inners.all():
            try:
                inner_values[ordering].append(Decimal(inner.value))
            except:
                pass

    # === Getter
    def get_value(ordering: str | list[str]) -> Decimal:
        if isinstance(ordering, str):
            return sum(inner_values.get(ordering, []))
        return sum(sum(inner_values.get(o, [])) for o in ordering)

    # === Hisoblash
    tayyorlangan_jami = (
        get_value(ordering_map["XOJALIK_JAMI"]) +
        get_value(ordering_map["XOJALIK_UCHASTKA"]) +
        get_value(ordering_map["BOSHQADAN_OLINDI"])
    )
    sarflangan_jami = get_value(ordering_map["SARFLANDI_KG_LIST"])
    oxirgi_qoldiq = (
        get_value(ordering_map["YIL_BOSHIGA_QOLDIQ"]) +
        tayyorlangan_jami -
        sarflangan_jami
    )

    # === Saqlash uchun cache
    to_create_items = []
    to_create_inners = []
    to_update_inners = []
    cached_values_for_new_items = {}  # ordering: value

    def buffer_value(ordering: str, value: Decimal):
        column = columns.get(ordering)
        if not column:
            return

        report_item = item_map.get(ordering)
        if report_item:
            inner = next(iter(report_item.inners.all()), None)
            if inner:
                inner.value = str(value)
                to_update_inners.append(inner)
            else:
                to_create_inners.append(ReportItemInner(
                    report_item=report_item,
                    value=str(value)
                ))
        else:
            report_item = ReportItem(
                report=report,
                statement_column=column
            )
            item_map[ordering] = report_item
            to_create_items.append(report_item)
            cached_values_for_new_items[ordering] = value  # ⬅️ Saqlab qo‘yamiz

    # Yozishlar
    buffer_value(ordering_map["JAMI_TAYYORLANDI"], tayyorlangan_jami)
    buffer_value(ordering_map["SARFLANDI_JAMI"], sarflangan_jami)
    buffer_value(ordering_map["OXIRGI_QOLDIQ"], oxirgi_qoldiq)

    # === Save block
    if to_create_items:
        ReportItem.objects.bulk_create(to_create_items)

        # assign va inner create
        for item in to_create_items:
            ordering = item.statement_column.ordering
            real_value = cached_values_for_new_items.get(ordering, Decimal(0))
            to_create_inners.append(ReportItemInner(
                report_item=item,
                value=str(real_value)
            ))

    if to_create_inners:
        ReportItemInner.objects.bulk_create(to_create_inners)

    if to_update_inners:
        ReportItemInner.objects.bulk_update(to_update_inners, ["value"])
