from collections import defaultdict
from decimal import Decimal
from apps.reports.models import Report, ReportItem, ReportItemInner


def calculate_seed_movement(report: Report):
    YEAR_START = "1.1.3"

    # Faqat REAL manbalar
    READY_PARTS = [
        "1.1.4.1.1.1",  # Xo‘jalik tomonidan
        "1.1.4.1.2.1",  # Boshqa tashkilotdan
    ]
    READY_TOTAL = "1.1.4.1"

    SPENT_PARTS = [
        "1.1.5.1.1.1",
        "1.1.5.1.2.1",
        "1.1.5.1.3.1",
        "1.1.5.1.4.1",
        "1.1.5.1.5.1",
    ]
    SPENT_TOTAL = "1.1.5.1"

    FINAL_REMAINS = "1.1.6"

    ALL_ORDERINGS = {
        YEAR_START,
        READY_TOTAL,
        SPENT_TOTAL,
        FINAL_REMAINS,
        *READY_PARTS,
        *SPENT_PARTS,
    }

    # === StatementColumnlar
    columns = {
        c.ordering: c
        for c in report.statement.columns.filter(ordering__in=ALL_ORDERINGS)
    }

    # === ReportItem + inners
    items = (
        ReportItem.objects
        .filter(report=report, statement_column__ordering__in=ALL_ORDERINGS)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    # ordering -> plant -> value
    values = defaultdict(lambda: defaultdict(Decimal))

    for item in items:
        ord_ = item.statement_column.ordering
        for inner in item.inners.all():
            if inner.plant_id:
                try:
                    values[ord_][inner.plant_id] += Decimal(inner.value)
                except:
                    pass

    def get(ordering, plant):
        return values.get(ordering, {}).get(plant, Decimal("0"))

    item_map = {i.statement_column.ordering: i for i in items}

    to_create_items = []
    to_create_inners = []
    to_update_inners = []

    def write(ordering, plant, value):
        if ordering not in columns:
            return

        item = item_map.get(ordering)
        if not item:
            item = ReportItem(report=report, statement_column=columns[ordering])
            item_map[ordering] = item
            to_create_items.append(item)

        existing = next(
            (i for i in item.inners.all() if i.plant_id == plant),
            None
        )

        if existing:
            existing.value = str(value)
            to_update_inners.append(existing)
        else:
            to_create_inners.append(
                ReportItemInner(
                    report_item=item,
                    plant_id=plant,
                    value=str(value)
                )
            )

    # === Plantlar
    # === Plantlar (sorted)
    plants = sorted({plant for v in values.values() for plant in v.keys()})

    # === HISOB
    for plant in plants:
        ready = sum(get(o, plant) for o in READY_PARTS)
        spent = sum(get(o, plant) for o in SPENT_PARTS)
        remains = get(YEAR_START, plant) + ready - spent

        write(READY_TOTAL, plant, ready)
        write(SPENT_TOTAL, plant, spent)
        write(FINAL_REMAINS, plant, remains)

    # === Save
    if to_create_items:
        ReportItem.objects.bulk_create(to_create_items)

    if to_create_inners:
        ReportItemInner.objects.bulk_create(to_create_inners)

    if to_update_inners:
        ReportItemInner.objects.bulk_update(to_update_inners, ["value"])


# def calculate_seed_movement(report: Report):
#     ordering_map = {
#         "YIL_BOSHIGA_QOLDIQ": "1.1.3",
#         "XOJALIK_JAMI": "1.1.4.1.1.1",
#         "XOJALIK_UCHASTKA": "1.1.4.1.1.2",
#         "BOSHQADAN_OLINDI": "1.1.4.1.2.1",
#         "JAMI_TAYYORLANDI": "1.1.4.1",
#         "SARFLANDI_JAMI": "1.1.5.1",
#         "SARFLANDI_KG_LIST": [
#             "1.1.5.1.1.1",
#             "1.1.5.1.2.1",
#             "1.1.5.1.3.1",
#             "1.1.5.1.4.1",
#             "1.1.5.1.5.1",
#         ],
#         "OXIRGI_QOLDIQ": "1.1.6",
#     }
#
#     # === ALL ORDERINGS
#     all_orderings = set()
#     for val in ordering_map.values():
#         all_orderings.update(val if isinstance(val, list) else [val])
#
#     # === Load statement columns
#     columns = {
#         col.ordering: col for col in
#         report.statement.columns.filter(ordering__in=all_orderings)
#     }
#
#     # === Load existing items and their inners
#     report_items = ReportItem.objects.filter(
#         report=report,
#         statement_column__ordering__in=all_orderings
#     ).select_related("statement_column").prefetch_related("inners")
#
#     item_map = {item.statement_column.ordering: item for item in report_items}
#
#     inner_values = defaultdict(list)
#     for item in report_items:
#         ordering = item.statement_column.ordering
#         for inner in item.inners.all():
#             try:
#                 inner_values[ordering].append(Decimal(inner.value))
#             except:
#                 pass
#
#     # === Getter
#     def get_value(ordering: str | list[str]) -> Decimal:
#         if isinstance(ordering, str):
#             return sum(inner_values.get(ordering, []))
#         return sum(sum(inner_values.get(o, [])) for o in ordering)
#
#     # === Hisoblash
#     tayyorlangan_jami = (
#         get_value(ordering_map["XOJALIK_JAMI"]) +
#         get_value(ordering_map["XOJALIK_UCHASTKA"]) +
#         get_value(ordering_map["BOSHQADAN_OLINDI"])
#     )
#     sarflangan_jami = get_value(ordering_map["SARFLANDI_KG_LIST"])
#     oxirgi_qoldiq = (
#         get_value(ordering_map["YIL_BOSHIGA_QOLDIQ"]) +
#         tayyorlangan_jami -
#         sarflangan_jami
#     )
#
#     # === Saqlash uchun cache
#     to_create_items = []
#     to_create_inners = []
#     to_update_inners = []
#     cached_values_for_new_items = {}  # ordering: value
#
#     def buffer_value(ordering: str, value: Decimal):
#         column = columns.get(ordering)
#         if not column:
#             return
#
#         report_item = item_map.get(ordering)
#         if report_item:
#             inner = next(iter(report_item.inners.all()), None)
#             if inner:
#                 inner.value = str(value)
#                 to_update_inners.append(inner)
#             else:
#                 to_create_inners.append(ReportItemInner(
#                     report_item=report_item,
#                     value=str(value)
#                 ))
#         else:
#             report_item = ReportItem(
#                 report=report,
#                 statement_column=column
#             )
#             item_map[ordering] = report_item
#             to_create_items.append(report_item)
#             cached_values_for_new_items[ordering] = value  # ⬅️ Saqlab qo‘yamiz
#
#     # Yozishlar
#     buffer_value(ordering_map["JAMI_TAYYORLANDI"], tayyorlangan_jami)
#     buffer_value(ordering_map["SARFLANDI_JAMI"], sarflangan_jami)
#     buffer_value(ordering_map["OXIRGI_QOLDIQ"], oxirgi_qoldiq)
#
#     # === Save block
#     if to_create_items:
#         ReportItem.objects.bulk_create(to_create_items)
#
#         # assign va inner create
#         for item in to_create_items:
#             ordering = item.statement_column.ordering
#             real_value = cached_values_for_new_items.get(ordering, Decimal(0))
#             to_create_inners.append(ReportItemInner(
#                 report_item=item,
#                 value=str(real_value)
#             ))
#
#     if to_create_inners:
#         ReportItemInner.objects.bulk_create(to_create_inners)
#
#     if to_update_inners:
#         ReportItemInner.objects.bulk_update(to_update_inners, ["value"])
