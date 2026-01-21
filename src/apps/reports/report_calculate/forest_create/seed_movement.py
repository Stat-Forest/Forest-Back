from collections import defaultdict
from decimal import Decimal, InvalidOperation
from apps.reports.models import Report, ReportItem, ReportItemInner


def calculate_seed_movement(report: Report):
    YEAR_START = "1.1.3"

    READY_PARTS = [
        "1.1.4.1.1.1",
        "1.1.4.1.2.1",
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

    # === ReportItem + Inners (oldindan yuklab olamiz)
    items = (
        ReportItem.objects
        .filter(report=report, statement_column__ordering__in=ALL_ORDERINGS)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    item_map = {item.statement_column.ordering: item for item in items}

    inners_map = {
        (item.statement_column.ordering, inner.plant_id): inner
        for item in items
        for inner in item.inners.all()
        if inner.plant_id
    }

    # ordering -> plant_id -> Decimal(value)
    values = defaultdict(lambda: defaultdict(Decimal))

    for item in items:
        ord_ = item.statement_column.ordering
        for inner in item.inners.all():
            if not inner.plant_id:
                continue
            try:
                values[ord_][inner.plant_id] += Decimal(inner.value or 0)
            except (InvalidOperation, TypeError):
                pass

    def get(ordering, plant_id):
        return values.get(ordering, {}).get(plant_id, Decimal("0"))

    to_create_items = []
    to_create_inners = []
    to_update_inners = []

    def write(ordering, plant_id, value):
        if ordering not in columns:
            return

        item = item_map.get(ordering)
        if not item:
            item = ReportItem(
                report=report,
                statement_column=columns[ordering],
            )
            item_map[ordering] = item
            to_create_items.append(item)

        key = (ordering, plant_id)
        existing = inners_map.get(key)

        if existing:
            existing.value = str(value)
            to_update_inners.append(existing)
        else:
            new_inner = ReportItemInner(
                report_item=item,
                plant_id=plant_id,
                value=str(value),
            )
            to_create_inners.append(new_inner)
            inners_map[key] = new_inner

    # ======================================================================
    # 🔑 ENG MUHIM QISM: ETALON PLANT ORDERING
    # ======================================================================
    def get_ordered_plants():
        """
        Plantlar ketma-ketligini user_input=True columnlardan olamiz.
        Bu frontend ko‘rayotgan REAL tartib.
        """
        base_item = (
            ReportItem.objects
            .filter(
                report=report,
                statement_column__is_user_input=True,
                inners__plant_id__isnull=False,
            )
            .prefetch_related("inners")
            .order_by("statement_column__ordering")
            .first()
        )

        if base_item:
            return [inner.plant_id for inner in base_item.inners.all()]

        # fallback (kamdan-kam holat)
        return sorted(
            {plant_id for plant_dict in values.values() for plant_id in plant_dict.keys()}
        )

    ordered_plants = get_ordered_plants()

    # ======================================================================
    # === HISOBLASH (logika o‘zgarmagan)
    # ======================================================================
    for plant_id in ordered_plants:
        ready = sum(get(o, plant_id) for o in READY_PARTS)
        spent = sum(get(o, plant_id) for o in SPENT_PARTS)
        remains = get(YEAR_START, plant_id) + ready - spent

        write(READY_TOTAL, plant_id, ready)
        write(SPENT_TOTAL, plant_id, spent)
        write(FINAL_REMAINS, plant_id, remains)

    # ======================================================================
    # === SAQLASH
    # ======================================================================
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
