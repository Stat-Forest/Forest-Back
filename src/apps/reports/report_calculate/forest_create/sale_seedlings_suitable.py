from decimal import Decimal
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn
from apps.reports.services.normalize_utils import normalize


def calculate_sale_seedlings(report: Report):
    title_column = (
        report.statement.columns
        .filter(ordering="1.1")
        .prefetch_related("children__children__children")
        .first()
    )
    if not title_column:
        return

    # Column larni cache qilamiz
    children_map = {
        col.id: sorted(col.children.all(), key=lambda c: c.ordering)
        for col in StatementColumn.objects.filter(statement=report.statement).prefetch_related("children")
    }

    # Oldingi qiymatlarni olish
    items = ReportItem.objects.filter(report=report).select_related("statement_column")
    inners = ReportItemInner.objects.filter(report_item__in=items).select_related("report_item")

    value_map = {}
    for inner in inners:
        col_id = inner.report_item.statement_column_id
        try:
            value_map.setdefault(col_id, []).append(float(inner.value))
        except (ValueError, TypeError):
            continue

    def sum_values_fast(statement_column):
        return sum(value_map.get(statement_column.id, []))

    # Yig‘iladigan obyektlar
    report_items_to_create = []
    inners_to_create = []

    total_soni = Decimal(0)
    total_summa = Decimal(0)

    sections = sorted(children_map.get(title_column.id, []), key=lambda c: c.ordering)
    for section in sections:
        children = children_map.get(section.id, [])
        if not children:
            continue

        jami_block = next((c for c in children if c.ordering.endswith(".1")), None)
        if not jami_block:
            continue

        jami_subchildren = children_map.get(jami_block.id, [])
        jami_soni_col = next((c for c in jami_subchildren if c.ordering.endswith(".1")), None)
        jami_summa_col = next((c for c in jami_subchildren if c.ordering.endswith(".2")), None)
        if not jami_soni_col or not jami_summa_col:
            continue

        plant_columns = [c for c in children if c.ordering > jami_block.ordering]

        section_soni = Decimal(0)
        section_summa = Decimal(0)

        for plant in plant_columns:
            if plant.title_uz.strip().lower() == "tashkilot nomi":
                continue

            soni_col = next((c for c in children_map.get(plant.id, []) if c.ordering.endswith(".1")), None)
            summa_col = next((c for c in children_map.get(plant.id, []) if c.ordering.endswith(".2")), None)
            if not soni_col or not summa_col:
                continue

            section_soni += normalize(sum_values_fast(soni_col))
            section_summa += normalize(sum_values_fast(summa_col))

        # Bulk obyektga tayyorlash
        if section_soni:
            item = ReportItem(report=report, statement_column=jami_soni_col)
            report_items_to_create.append((item, str(section_soni)))

        if section_summa:
            item = ReportItem(report=report, statement_column=jami_summa_col)
            report_items_to_create.append((item, str(section_summa)))

        total_soni += section_soni
        total_summa += section_summa

    # Umumiy jami
    root_jami = report.statement.columns.filter(ordering="1.1.2").first()
    if root_jami:
        children = children_map.get(root_jami.id, [])
        jami_soni_col = next((c for c in children if c.ordering.endswith(".1")), None)
        jami_summa_col = next((c for c in children if c.ordering.endswith(".2")), None)

        if jami_soni_col and total_soni:
            item = ReportItem(report=report, statement_column=jami_soni_col)
            report_items_to_create.append((item, str(total_soni)))

        if jami_summa_col and total_summa:
            item = ReportItem(report=report, statement_column=jami_summa_col)
            report_items_to_create.append((item, str(total_summa)))

    # Endi barcha ReportItem`larni bir marta saqlaymiz
    report_item_models = [item for item, _ in report_items_to_create]
    ReportItem.objects.bulk_create(report_item_models)

    # ReportItemInner`larni tayyorlaymiz
    for (item, value), saved_item in zip(report_items_to_create, report_item_models):
        inners_to_create.append(ReportItemInner(report_item=saved_item, value=value))

    # Bulk insert
    ReportItemInner.objects.bulk_create(inners_to_create)
