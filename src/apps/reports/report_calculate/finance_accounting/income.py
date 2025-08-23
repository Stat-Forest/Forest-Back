from collections import defaultdict
from decimal import Decimal, InvalidOperation
from django.db import transaction

from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn


def calculate_income_summary(report: Report):
    statement = report.statement
    columns = statement.columns.prefetch_related("children").all()
    col_map = {col.ordering: col for col in columns if col.ordering}

    # ReportItems va Innersni oldindan chaqirib olish
    report_items = ReportItem.objects.filter(report=report).select_related("statement_column")
    report_item_map = {item.statement_column_id: item for item in report_items}

    inners = ReportItemInner.objects.filter(report_item__in=report_items)
    inner_map = defaultdict(list)
    for inner in inners:
        inner_map[inner.report_item_id].append(inner)

    updated_inners = []
    created_items = []
    created_inners = []

    def create_calculated_items(column: StatementColumn, value: Decimal):
        rounded = str(round(value, 2))
        item = report_item_map.get(column.id)

        if item:
            inner_list = inner_map.get(item.id)
            if inner_list:
                inner = inner_list[0]
                inner.value = rounded
                updated_inners.append(inner)
            else:
                inner = ReportItemInner(report_item=item, value=rounded)
                created_inners.append(inner)
                inner_map[item.id].append(inner)
        else:
            item = ReportItem(report=report, statement_column=column)
            created_items.append(item)
            report_item_map[column.id] = item

            inner = ReportItemInner(report_item=item, value=rounded)
            created_inners.append(inner)
            inner_map[item.id].append(inner)

    def sum_values(columns: list[StatementColumn]) -> Decimal:
        total = Decimal("0")
        for col in columns:
            item = report_item_map.get(col.id)
            if not item:
                continue
            for inner in inner_map.get(item.id, []):
                try:
                    total += Decimal(str(inner.value))
                except (InvalidOperation, TypeError, ValueError):
                    continue
        return total

    # === 1.1 blok (1-ilova) ===
    for column in columns:
        if column.ordering == "1.1":
            input_columns = []
            jami_column = None

            for child in column.children.all():
                if not child.ordering:
                    continue
                if child.ordering.startswith("1.1."):
                    if child.ordering == "1.1.19":
                        jami_column = child
                    else:
                        input_columns.append(child)

            if jami_column:
                total = sum_values(input_columns)
                create_calculated_items(jami_column, total)

    # === Oylar uchun foizlar ===
    oy_ordering_list = [
        "2.1.4.1", "2.1.4.2", "2.1.4.3",
        "2.1.6.1", "2.1.6.2", "2.1.6.3",
        "2.1.8.1", "2.1.8.2", "2.1.8.3",
        "2.1.10.1", "2.1.10.2", "2.1.10.3",
    ]

    for oy in oy_ordering_list:
        reja = sum_values([col_map.get(f"{oy}.1")])
        amalda = sum_values([col_map.get(f"{oy}.2")])
        foiz_col = col_map.get(f"{oy}.3")

        if foiz_col:
            foiz = (amalda / reja * 100) if reja > 0 else Decimal(0)
            create_calculated_items(foiz_col, foiz)

    # === Chorak amalda ===
    chorak_map = {
        "2.1.3.2": ["2.1.4.1.2", "2.1.4.2.2", "2.1.4.3.2"],
        "2.1.5.2": ["2.1.6.1.2", "2.1.6.2.2", "2.1.6.3.2"],
        "2.1.7.2": ["2.1.8.1.2", "2.1.8.2.2", "2.1.8.3.2"],
        "2.1.9.2": ["2.1.10.1.2", "2.1.10.2.2", "2.1.10.3.2"],
    }

    chorak_amaldas = []

    for chorak_ordering, oy_orderings in chorak_map.items():
        oy_columns = [col_map.get(o) for o in oy_orderings if col_map.get(o)]
        total = sum_values(oy_columns)

        chorak_col = col_map.get(chorak_ordering)
        if chorak_col:
            create_calculated_items(chorak_col, total)
            chorak_amaldas.append(total)

    # === Yil boshidan tushum: 2.1.11.1 ===
    year_begin_col = col_map.get("2.1.11.1")
    if year_begin_col:
        total = sum(chorak_amaldas, Decimal(0))
        create_calculated_items(year_begin_col, total)

    # === Yillik reja nisbatan %: 2.1.11.2 ===
    yearly_plan_col = col_map.get("2.1.2")
    foiz_col = col_map.get("2.1.11.2")
    if yearly_plan_col and foiz_col:
        reja = sum_values([yearly_plan_col])
        foiz = (total / reja * 100) if reja > 0 else Decimal(0)
        create_calculated_items(foiz_col, foiz)

    # === ✅ 3-Ilova (Svod) — 2.1.2 va 2.1.11.1 asosida hisoblash ===
    svod_reja_col = col_map.get("3.1.2")
    svod_amalda_col = col_map.get("3.1.3")
    svod_foiz_col = col_map.get("3.1.4")

    if svod_reja_col:
        reja = sum_values([col_map.get("2.1.2")])
        create_calculated_items(svod_reja_col, reja)

    if svod_amalda_col:
        amalda = sum(chorak_amaldas, Decimal(0))
        create_calculated_items(svod_amalda_col, amalda)

    if svod_foiz_col:
        reja = sum_values([col_map.get("2.1.2")])
        amalda = sum(chorak_amaldas, Decimal(0))
        foiz = (amalda / reja * 100) if reja > 0 else Decimal(0)
        create_calculated_items(svod_foiz_col, foiz)

    # === BULK SAVE ===
    with transaction.atomic():
        if created_items:
            ReportItem.objects.bulk_create(created_items)
        if created_inners:
            ReportItemInner.objects.bulk_create(created_inners)
        if updated_inners:
            ReportItemInner.objects.bulk_update(updated_inners, ["value"])
