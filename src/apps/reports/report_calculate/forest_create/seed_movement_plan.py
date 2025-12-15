from decimal import Decimal, InvalidOperation
from collections import defaultdict

from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn
from apps.reports.services.get_two_numbers_in_percent import round_decimal


def normalize(value):
    try:
        if value in (None, ""):
            return Decimal("0")
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def calculate_seed_movement_plan(report: Report):
    """
    Urug‘ xarakati Reja uchun FOIZ hisoblash.

    - Oddiy tashkilotda REJA va FOIZ = 0 (faqat ko‘rinishda)
    - Tashkilot JAMI (is_individual_general=True) uchun:
        - FOIZ = (AMALDA / REJA) * 100
    """

    if report.statement.name_uz.strip() != "Urug' xarakati Reja":
        return

    ordering_map = {
        "REJA": "1.1.2.1",
        "AMALDA": "1.1.2.2",
        "FOIZ": "1.1.2.3",
    }

    # 1️⃣ ReportItemlarni olish
    report_items = (
        ReportItem.objects
        .filter(report=report)
        .select_related("statement_column")
        .prefetch_related("inners")
    )
    report_item_map = {
        item.statement_column.ordering: item
        for item in report_items
    }

    # 2️⃣ UMUMIY REJA (plant=None)
    umumiy_reja = Decimal("0")
    reja_item = report_item_map.get(ordering_map["REJA"])

    if reja_item:
        umumiy_inner = reja_item.inners.filter(plant__isnull=True).first()
        if umumiy_inner:
            umumiy_reja = normalize(umumiy_inner.value)

            # 🛑 Oddiy tashkilotlarda REJA butunlay ko'rinmasin (plant=None ham, plantli ham 0 bo'lsin)
            if not report.is_individual_general:
                updates = []
                # plant=None qiymatini 0 qilish
                if umumiy_inner.value != "0":
                    umumiy_inner.value = "0"
                    updates.append(umumiy_inner)
                # plant bor barcha innerlarni 0 qilish
                for inner in reja_item.inners.exclude(id=umumiy_inner.id):
                    if inner.value != "0":
                        inner.value = "0"
                        updates.append(inner)
                if updates:
                    ReportItemInner.objects.bulk_update(updates, ["value"])

    # 3️⃣ AMALDA (plant bo‘yicha yoki organization-level)
    amalda_map = defaultdict(Decimal)
    amalda_item = report_item_map.get(ordering_map["AMALDA"])
    org_level_amalda = None
    if amalda_item:
        for inner in amalda_item.inners.all():
            if inner.plant_id:
                amalda_map[inner.plant_id] += normalize(inner.value)
            else:
                # plant=None bo'lgan AMALDA (tashkilot darajasida)
                org_level_amalda = normalize(inner.value)

    # 4️⃣ FOIZ = 0 → agar oddiy report
    if not report.is_individual_general:
        foiz_item = report_item_map.get(ordering_map["FOIZ"])
        if foiz_item:
            for inner in foiz_item.inners.all():
                if inner.value != "0":
                    inner.value = "0"
                    inner.save(update_fields=["value"])
        return  # FOIZ hisoblanmasin

    # 5️⃣ FOIZ ustuni (mustahkamlash)
    foiz_col = StatementColumn.objects.filter(
        statement=report.statement,
        ordering=ordering_map["FOIZ"]
    ).first()

    if not foiz_col:
        return

    foiz_item = report_item_map.get(ordering_map["FOIZ"])
    if not foiz_item:
        foiz_item = ReportItem.objects.create(
            report=report,
            statement_column=foiz_col
        )

    # 6️⃣ FOIZni faqat tashkilot darajasida (plant=None) hisoblash
    #    AMALDA umumiy yig'indisi olinadi
    # Agar organization-level AMALDA mavjud bo'lsa, undan foydalanamiz,
    # aks holda plant-level yig'indisini ishlatamiz
    total_amalda = org_level_amalda if org_level_amalda is not None else sum(amalda_map.values(), Decimal("0"))
    foiz_val = (total_amalda / umumiy_reja * 100) if umumiy_reja else Decimal("0")
    foiz_val = round_decimal(foiz_val)

    # Avvalo plantli eski foiz innerslarni olib tashlaymiz
    foiz_item.inners.filter(plant__isnull=False).delete()

    org_inner = foiz_item.inners.filter(plant__isnull=True).first()
    if not org_inner:
        ReportItemInner.objects.create(
            report_item=foiz_item,
            value=str(foiz_val)
        )
    else:
        if normalize(org_inner.value) != foiz_val:
            org_inner.value = str(foiz_val)
            org_inner.save(update_fields=["value"])

    print("✅ FOIZ hisoblandi (organization-level)")
