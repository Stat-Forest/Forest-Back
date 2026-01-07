from decimal import Decimal
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn
from apps.reports.services.get_two_numbers_in_percent import round_decimal


def normalize(value) -> Decimal:
    """String yoki None tipdagi qiymatni Decimal ga xavfsiz aylantiradi."""
    try:
        return Decimal(str(value)) if value not in (None, "") else Decimal("0")
    except (ValueError, TypeError):
        return Decimal("0")


def sum_org_level(item: ReportItem) -> Decimal:
    """
    Faqat plant=None bo‘lgan ReportItemInner’lar qiymatini yig‘adi.
    """
    if not item:
        return Decimal("0")
    return sum([normalize(inn.value) for inn in item.inners.filter(plant__isnull=True)], Decimal("0"))


def calculate_heavy_neighborhood(report: Report) -> None:
    """
    Og‘ir mahalla hisobotida FOIZ (1.1.6) ni hisoblaydi:
    FOIZ = AMALDA / REJA * 100 (faqat plant=None bo‘yicha)

    - Reja:   ordering = 1.1.4
    - Amalda: ordering = 1.1.5
    - Foiz:   ordering = 1.1.6
    - Faqat `is_individual_general` bo‘lgan reportlar uchun FOIZ hisoblanadi
    """
    ORDERING_MAP = {
        "REJA": "1.1.4",
        "AMALDA": "1.1.5",
        "FOIZ": "1.1.6",
    }

    # 1. ReportItemlarni oldindan olish (optimized query)
    items = (
        report.report_items
        .filter(statement_column__ordering__in=ORDERING_MAP.values())
        .select_related("statement_column")
        .prefetch_related("inners")
    )
    item_map = {item.statement_column.ordering: item for item in items}

    reja_item = item_map.get(ORDERING_MAP["REJA"])
    amalda_item = item_map.get(ORDERING_MAP["AMALDA"])
    foiz_item = item_map.get(ORDERING_MAP["FOIZ"])

    reja_sum = sum_org_level(reja_item)
    amalda_sum = sum_org_level(amalda_item)

    # 2. Agar report oddiy tashkilotniki bo‘lsa (is_individual_general emas)
    if not report.is_individual_general:
        # 1) FOIZni 0 ga tushiramiz
        if foiz_item:
            for inner in foiz_item.inners.filter(plant__isnull=True):
                if inner.value != "0":
                    inner.value = "0"
                    inner.save(update_fields=["value"])
        # 2) REJAdagi organization-level innersni ham 0 qilamiz
        if reja_item:
            updates = []
            for inner in reja_item.inners.filter(plant__isnull=True):
                if inner.value != "0":
                    inner.value = "0"
                    updates.append(inner)
            # agar plantli inners bo'lsa — hammasini 0 qilamiz (bu statement plantli emas)
            for inner in reja_item.inners.filter(plant__isnull=False):
                if inner.value != "0":
                    inner.value = "0"
                    updates.append(inner)
            if updates:
                from apps.reports.models import ReportItemInner
                ReportItemInner.objects.bulk_update(updates, ["value"])
        return

    # 3. Aks holda FOIZ = AMALDA / REJA * 100 ni hisoblaymiz
    foiz_value = round_decimal(
        (amalda_sum / reja_sum * 100) if reja_sum else Decimal("0"),
        places=1
    )

    # 4. Agar FOIZ uchun item mavjud bo‘lmasa — yaratamiz
    if not foiz_item:
        foiz_column = StatementColumn.objects.filter(
            statement=report.statement,
            ordering=ORDERING_MAP["FOIZ"]
        ).first()
        if not foiz_column:
            return  # Agar FOIZ column topilmasa, hech narsa qilmaymiz
        foiz_item = ReportItem.objects.create(
            report=report,
            statement_column=foiz_column
        )

    # 5. Eski plantli qiymatlar bo‘lsa — o‘chirib yuboramiz
    foiz_item.inners.filter(plant__isnull=False).delete()

    # 6. Org-level (plant=None) qiymatini yangilaymiz yoki yaratamiz
    org_inner = foiz_item.inners.filter(plant__isnull=True).first()
    if not org_inner:
        ReportItemInner.objects.create(
            report_item=foiz_item,
            value=str(foiz_value)
        )
    elif normalize(org_inner.value) != foiz_value:
        org_inner.value = str(foiz_value)
        org_inner.save(update_fields=["value"])
