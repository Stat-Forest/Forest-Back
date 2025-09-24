from collections import defaultdict
from decimal import Decimal
from apps.reports.models import ReportItem, Report, ReportItemInner
from apps.reports.report_calculate.additional_use_forests.get_general_columns import calculate_kx_svod_from_8_app
from apps.reports.report_calculate.additional_use_forests.k_x_svod import calculate_kxsvod


def calculate_qishloq_xojaligi(report: Report):
    """
    Qishloq xo‘jaligi ilovalari hisoblash:
    Har bir blok (ilova) o‘zidagi ekinlar summasini umumiy ustunga qo‘shadi.
    """

    columns = report.statement.columns.select_related("parent").all()

    # ==================== Moyli ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="4.1.2",  # Moyli ekinlar jami
        crop_orderings=["4.1.3.1", "4.1.3.2", "4.1.3.3", "4.1.3.4", "4.1.3.5"]
    )

    # ==================== Bodom va Pista ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="8.1.2",  # Jami yong‘oqmevalilar
        crop_orderings=["8.1.3.1", "8.1.3.2", "8.1.3.3"]
    )

    # ==================== Boshoqli Don ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="1.1.2",
        crop_orderings=["1.1.4.1", "1.1.4.2", "1.1.4.3", "1.1.4.4", "1.1.4.5", "1.1.4.6"]
    )

    # ==================== Sabzavot ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="2.1.2",
        crop_orderings=[
            "2.1.3.1", "2.1.3.2", "2.1.3.3", "2.1.3.4", "2.1.3.5", "2.1.3.6",
            "2.1.3.7", "2.1.3.8", "2.1.3.9", "2.1.3.10", "2.1.3.11", "2.1.3.12"
        ]
    )

    # ==================== Poliz ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="3.1.2",
        crop_orderings=[
            "3.1.3.1", "3.1.3.2", "3.1.3.3"
        ]
    )

    # ==================== Dukkakli ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="5.1.2",
        crop_orderings=[
            "5.1.3.1", "5.1.3.2", "5.1.3.3", "5.1.3.4"
        ]
    )

    # ==================== Ozuqa ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="6.1.2",
        crop_orderings=[
            "6.1.3.1", "6.1.3.2", "6.1.3.3", "6.1.3.4"
        ]
    )

    # ==================== Bog` Tok ilovasi ====================
    calculate_ilova(
        report=report,
        columns=columns,
        parent_ordering="7.1.2",
        crop_orderings=[
            "7.1.3.1", "7.1.3.2", "7.1.3.3"
        ]
    )
    # ==================== K-X SVOD Jami Columnlani get qib ob kelish ====================
    calculate_kx_svod_from_8_app(report, columns)

    # ==================== K-X SVOD(9-ilova) ====================
    calculate_kxsvod(report, columns)

def calculate_ilova(report, columns, parent_ordering: str, crop_orderings: list[str]):
    from django.db import transaction
    from collections import defaultdict
    from decimal import Decimal

    suffix_map = {"1": "ga", "2": "s/ga", "3": "tn", "4": "tn"}
    result = defaultdict(Decimal)

    # 1. Jami ustunlari
    parent_cols = {
        suffix_map.get(col.ordering.rsplit(".", 1)[-1]): col
        for col in columns
        if col.parent and col.parent.ordering == parent_ordering
    }
    parent_col_ids = [col.id for col in parent_cols.values()]

    # 2. Barcha item va innerlarni keltiramiz
    all_items = list(
        ReportItem.objects.filter(report=report)
        .select_related("statement_column")
        .prefetch_related("inners")
    )
    item_map = {item.statement_column.ordering: item for item in all_items if item.statement_column}

    # 3. Prefetched innersni cache ga joylaymiz
    inners_map = {}
    for item in all_items:
        if item.statement_column:
            # inners.all() har doim list bo'lishi uchun
            item_inners = list(item.inners.all())
            inners_map[item.statement_column.ordering] = item_inners

    # 4. Crop ustunlarni yig‘amiz
    for col in columns:
        if any(col.ordering.startswith(order) for order in crop_orderings):
            suffix = col.ordering.rsplit(".", 1)[-1]
            key = suffix_map.get(suffix)
            if not key:
                continue

            item = item_map.get(col.ordering)
            inner = inners_map.get(col.ordering, [])
            if item and inner:
                try:
                    result[key] += Decimal(inner[0].value or 0)
                except:
                    pass

    # 5. Yozuvlarni yangilaymiz
    existing_items = {
        item.statement_column_id: item
        for item in all_items
        if item.statement_column_id in parent_col_ids
    }

    new_items_to_create = []
    new_inners_to_create = []
    update_inners = []

    with transaction.atomic():
        for key, total_value in result.items():
            parent_col = parent_cols.get(key)
            if not parent_col:
                continue

            item = existing_items.get(parent_col.id)
            if item:
                inner_list = inners_map.get(parent_col.ordering, [])
                if inner_list:
                    inner_list[0].value = str(total_value)
                    update_inners.append(inner_list[0])
                else:
                    new_inners_to_create.append(
                        ReportItemInner(report_item=item, value=str(total_value))
                    )
            else:
                new_items_to_create.append(ReportItem(
                    report=report,
                    statement_column=parent_col
                ))

        ReportItem.objects.bulk_create(new_items_to_create)

        # Reload new items
        created_items = ReportItem.objects.filter(
            report=report,
            statement_column__in=[i.statement_column for i in new_items_to_create]
        )
        created_map = {item.statement_column_id: item for item in created_items}

        for key, total_value in result.items():
            parent_col = parent_cols.get(key)
            if not parent_col:
                continue
            if parent_col.id in created_map:
                new_item = created_map[parent_col.id]
                new_inners_to_create.append(
                    ReportItemInner(report_item=new_item, value=str(total_value))
                )

        if new_inners_to_create:
            ReportItemInner.objects.bulk_create(new_inners_to_create)
        if update_inners:
            ReportItemInner.objects.bulk_update(update_inners, ["value"])
