from decimal import Decimal
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn
from apps.reports.services.get_two_numbers_in_percent import round_decimal


def normalize(value):
    try:
        return Decimal(str(value)) if value not in (None, "") else Decimal("0")
    except Exception:
        return Decimal("0")


def sum_org_level_cached(item):
    if not item:
        return Decimal("0")

    total = Decimal("0")
    for inner in item.inners.all():   # prefetch cache ishlaydi
        if inner.plant_id is None:
            total += normalize(inner.value)
    return total


def calculate_heavy_neighborhood(report: Report):

    ORDERING = {
        "REJA": "1.1.4",
        "AMALDA": "1.1.5",
        "FOIZ": "1.1.6",
    }

    items = (
        report.report_items
        .filter(statement_column__ordering__in=ORDERING.values())
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    item_map = {i.statement_column.ordering: i for i in items}

    reja_item = item_map.get(ORDERING["REJA"])
    amalda_item = item_map.get(ORDERING["AMALDA"])
    foiz_item = item_map.get(ORDERING["FOIZ"])

    reja_sum = sum_org_level_cached(reja_item)
    amalda_sum = sum_org_level_cached(amalda_item)

    # =====================================================
    # 🚫 ODDIY REPORT — hammasini tozalaymiz
    # =====================================================
    if not report.is_individual_general:

        updates = []

        if foiz_item:
            for inner in foiz_item.inners.all():
                if inner.value != "0":
                    inner.value = "0"
                    updates.append(inner)

        if reja_item:
            for inner in reja_item.inners.all():
                if inner.value != "0":
                    inner.value = "0"
                    updates.append(inner)

        if updates:
            ReportItemInner.objects.bulk_update(updates, ["value"])

        return

    # =====================================================
    # ✅ JAMIDA FOIZ HISOBLAYMIZ
    # =====================================================
    foiz_val = round_decimal(
        (amalda_sum / reja_sum * 100) if reja_sum else Decimal("0"),
        places=1
    )

    if not foiz_item:
        foiz_col = StatementColumn.objects.filter(
            statement=report.statement,
            ordering=ORDERING["FOIZ"]
        ).first()
        if not foiz_col:
            return

        foiz_item = ReportItem.objects.create(
            report=report,
            statement_column=foiz_col
        )

    # plantli eski qiymatlarni o‘chiramiz
    foiz_item.inners.filter(plant__isnull=False).delete()

    org_inner = None
    for inner in foiz_item.inners.all():
        if inner.plant_id is None:
            org_inner = inner
            break

    if not org_inner:
        ReportItemInner.objects.create(
            report_item=foiz_item,
            value=str(foiz_val)
        )
    elif normalize(org_inner.value) != foiz_val:
        org_inner.value = str(foiz_val)
        org_inner.save(update_fields=["value"])
