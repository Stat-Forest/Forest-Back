from decimal import Decimal
from apps.reports.models import Report, ReportItem, ReportItemInner


def create_calculated_items(report, column, value):
    if not column:
        return
    ReportItem.objects.filter(report=report, statement_column=column).delete()
    item = ReportItem.objects.create(
        report=report,
        statement_column=column
    )
    ReportItemInner.objects.create(
        report_item=item,
        value=str(value)
    )


def calculate_forest_statement(report: Report):
    ordering_map = {
        "JAMI_REJA": "1.1.2.1",
        "JAMI_AMALDA": "1.1.2.2",
        "JAMI_FOIZ": "1.1.2.3",

        "CHOL_REJA": "1.1.3.1",
        "CHOL_AMALDA": "1.1.3.2",
        "CHOL_FOIZ": "1.1.3.3",

        "YONGOQ_AMALDA_LIST": ["1.1.5.1", "1.1.5.2", "1.1.5.3"],
        "JAMI_YONGOQ_REJA": "1.1.4.1",
        "JAMI_YONGOQ_AMALDA": "1.1.4.2",
        "JAMI_YONGOQ_FOIZ": "1.1.4.3",

        "TEZ_OSUVCHILAR_AMALDA_LIST": [
            "1.1.7.1", "1.1.7.2", "1.1.7.3", "1.1.7.4", "1.1.7.5", "1.1.7.6", "1.1.7.7"
        ],
        "JAMI_TEZ_OSUVCHILAR_REJA": "1.1.6.1",
        "JAMI_TEZ_OSUVCHILAR_AMALDA": "1.1.6.2",
        "JAMI_TEZ_OSUVCHILAR_FOIZ": "1.1.6.3",

        "TABIIY_TIKLANISH_AMALDA": "1.1.8",
    }

    all_columns = report.statement.columns.prefetch_related("children").all()
    columns_by_ordering = {col.ordering: col for col in all_columns}

    # 🔽 Barcha ReportItem + Inner ni oldindan olib kelamiz
    report_items = (
        ReportItem.objects
        .filter(report=report)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    # 🔽 column_id => summa dict
    column_value_map = {}

    for item in report_items:
        total = Decimal(0)
        for inner in item.inners.all():
            try:
                total += Decimal(str(inner.value or 0))
            except:
                continue
        column_value_map[item.statement_column.ordering] = total

    def get_amalda_sum(orderings: list | str) -> Decimal:
        if isinstance(orderings, str):
            orderings = [orderings]
        return sum(column_value_map.get(o, Decimal(0)) for o in orderings)

    # 🔽 Hisoblashlar
    chol_amalda = get_amalda_sum(ordering_map["CHOL_AMALDA"])
    yongoq_amalda = get_amalda_sum(ordering_map["YONGOQ_AMALDA_LIST"])
    tez_osuvchilar_amalda = get_amalda_sum(ordering_map["TEZ_OSUVCHILAR_AMALDA_LIST"])
    tabiiy_amalda = get_amalda_sum(ordering_map["TABIIY_TIKLANISH_AMALDA"])
    jami_amalda = chol_amalda + yongoq_amalda + tez_osuvchilar_amalda + tabiiy_amalda

    # 🔽 Natijalarni saqlash
    create_calculated_items(report, columns_by_ordering.get(ordering_map["JAMI_YONGOQ_AMALDA"]), yongoq_amalda)
    create_calculated_items(report, columns_by_ordering.get(ordering_map["JAMI_TEZ_OSUVCHILAR_AMALDA"]), tez_osuvchilar_amalda)
    create_calculated_items(report, columns_by_ordering.get(ordering_map["JAMI_AMALDA"]), jami_amalda)

    def calc_foiz(reja_ord, amalda_val, foiz_ord):
        reja_val = column_value_map.get(reja_ord, Decimal(0))
        foiz = (amalda_val / reja_val * 100) if reja_val else Decimal(0)
        create_calculated_items(report, columns_by_ordering.get(foiz_ord), foiz)

    # 🔽 Foizlar
    calc_foiz(ordering_map["JAMI_REJA"], jami_amalda, ordering_map["JAMI_FOIZ"])
    calc_foiz(ordering_map["CHOL_REJA"], chol_amalda, ordering_map["CHOL_FOIZ"])
    calc_foiz(ordering_map["JAMI_YONGOQ_REJA"], yongoq_amalda, ordering_map["JAMI_YONGOQ_FOIZ"])
    calc_foiz(ordering_map["JAMI_TEZ_OSUVCHILAR_REJA"], tez_osuvchilar_amalda, ordering_map["JAMI_TEZ_OSUVCHILAR_FOIZ"])
