from decimal import Decimal, InvalidOperation

from apps.reports.models import Report, ReportItem, ReportItemInner


def normalize_decimal(value) -> Decimal:
    """
    Xatoliklar chiqmasligi uchun xavfsiz Decimal convertor.
    """
    try:
        if value is None or value == "":
            return Decimal(0)
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(0)


def create_calculated_items(report: Report, column, value: Decimal):
    item, _ = ReportItem.objects.get_or_create(
        report=report,
        statement_column=column
    )
    ReportItemInner.objects.update_or_create(
        report_item=item,
        defaults={"value": str(value)}
    )


def calculate_forest_statement(report: Report):
    ordering_map = {
        "JAMI_REJA": "1.1.2.1",
        "JAMI_AMALDA": "1.1.2.2",
        "JAMI_FOIZ": "1.1.2.3",

        "JAMI_YONGOQ_AMALDA": "1.1.7",
        "YONGOQ_AMALDA_LIST": ["1.1.8.1", "1.1.8.2", "1.1.8.3"],

        "JAMI_TEZ_OSUVCHILAR_REJA": "1.1.9.1",
        "JAMI_TEZ_OSUVCHILAR_AMALDA": "1.1.9.2",
        "JAMI_TEZ_OSUVCHILAR_FOIZ": "1.1.9.3",
        "TEZ_OSUVCHILAR_AMALDA_LIST": [
            "1.1.10.1", "1.1.10.2", "1.1.10.3", "1.1.10.4",
            "1.1.10.5", "1.1.10.6", "1.1.10.7"
        ],

        "TABIIY_TIKLANISH_AMALDA": "1.1.11",

        "ODDIY_BO_LIMLAR_AMALDA_LIST": [
            "1.1.3.2", "1.1.4.2", "1.1.5.2", "1.1.6.2"
        ]
    }

    # === Columnlar cache
    columns_by_ordering = {
        col.ordering: col for col in report.statement.columns.all()
    }

    # === Barcha ReportItem va ReportItemInner oldindan
    report_items = (
        ReportItem.objects.filter(report=report)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    # === Keshlar
    column_value_map = {}
    existing_items = {}
    for item in report_items:
        ordering = item.statement_column.ordering
        existing_items[ordering] = item
        total = sum(normalize_decimal(inner.value) for inner in item.inners.all())
        column_value_map[ordering] = total

    def get_sum(orderings):
        if isinstance(orderings, str):
            orderings = [orderings]
        return sum(column_value_map.get(o, Decimal(0)) for o in orderings)

    def save_value(ordering: str, value: Decimal):
        column = columns_by_ordering.get(ordering)
        if not column:
            return

        item = existing_items.get(ordering)
        if item:
            inner = item.inners.first()
            if inner:
                # faqat qiymat o‘zgargan bo‘lsa, update qilamiz
                if Decimal(str(inner.value or 0)) != value:
                    inner.value = str(value)
                    inner.save(update_fields=["value"])
            else:
                ReportItemInner.objects.create(report_item=item, value=str(value))
        else:
            # yangi item
            new_item = ReportItem.objects.create(
                report=report,
                statement_column=column
            )
            ReportItemInner.objects.create(
                report_item=new_item,
                value=str(value)
            )
            existing_items[ordering] = new_item  # cache ga qo‘shamiz

    # === Hisoblash
    oddiy_amalda = get_sum(ordering_map["ODDIY_BO_LIMLAR_AMALDA_LIST"])
    yongoq_amalda = get_sum(ordering_map["YONGOQ_AMALDA_LIST"])
    tez_osuvchilar_amalda = get_sum(ordering_map["TEZ_OSUVCHILAR_AMALDA_LIST"])
    tabiiy_amalda = get_sum(ordering_map["TABIIY_TIKLANISH_AMALDA"])
    jami_amalda = oddiy_amalda + yongoq_amalda + tez_osuvchilar_amalda + tabiiy_amalda

    # === Saqlash
    save_value(ordering_map["JAMI_AMALDA"], oddiy_amalda)
    save_value(ordering_map["JAMI_YONGOQ_AMALDA"], yongoq_amalda)
    save_value(ordering_map["JAMI_TEZ_OSUVCHILAR_AMALDA"], tez_osuvchilar_amalda)

    def calc_foiz(reja_ord, amalda_val, foiz_ord):
        reja_val = column_value_map.get(reja_ord, Decimal(0))
        foiz = (amalda_val / reja_val * 100) if reja_val else Decimal(0)
        save_value(foiz_ord, foiz)

    # === Foiz
    calc_foiz(ordering_map["JAMI_REJA"], oddiy_amalda, ordering_map["JAMI_FOIZ"])
    calc_foiz(ordering_map["JAMI_TEZ_OSUVCHILAR_REJA"], tez_osuvchilar_amalda, ordering_map["JAMI_TEZ_OSUVCHILAR_FOIZ"])
