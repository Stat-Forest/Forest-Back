from uuid import UUID
from decimal import Decimal, InvalidOperation
from collections import defaultdict

from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn
from apps.reports.services.get_two_numbers_in_percent import round_decimal


def normalize(value):
    try:
        if value is None or value == "":
            return Decimal("0")
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def calculate_seed_movement_plan(report: Report):
    """
    Urug‘ xarakati (plant-based) uchun:
    Reja (1.1.2.1), Amalda (1.1.2.2) → Foiz (1.1.2.3)
    """
    ordering_map = {
        "REJA": "1.1.2.1",
        "AMALDA": "1.1.2.2",
        "FOIZ": "1.1.2.3",
    }

    # 🔍 Oldindan barcha ReportItem va ularning innerslarini yuklab olamiz
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

    # 🔢 Har bir ordering uchun plant_id → value mapping
    def get_plant_value_map(ordering: str) -> dict[UUID, Decimal]:
        item = report_item_map.get(ordering)
        if not item:
            return {}
        totals = defaultdict(Decimal)
        for inner in item.inners.all():
            if inner.plant_id:
                totals[inner.plant_id] += normalize(inner.value)
        return totals

    reja_map = get_plant_value_map(ordering_map["REJA"])
    amalda_map = get_plant_value_map(ordering_map["AMALDA"])

    # 🔁 Ketma-ketlikni saqlaymiz: agar reja bo‘lmasa fallback = amalda
    plant_order = list(reja_map.keys()) or list(amalda_map.keys())

    # 📈 Foiz = (amalda / reja) * 100
    foiz_map = defaultdict(Decimal)
    for pid in set(reja_map.keys()) | set(amalda_map.keys()):
        reja_val = reja_map.get(pid, Decimal("0"))
        amalda_val = amalda_map.get(pid, Decimal("0"))
        foiz = (amalda_val / reja_val * 100) if reja_val else Decimal("0")
        foiz_map[pid] = round_decimal(foiz)

    # 🧩 Foiz ustunini topamiz
    foiz_col = StatementColumn.objects.filter(
        statement=report.statement,
        ordering=ordering_map["FOIZ"]
    ).first()
    if not foiz_col:
        return  # Ustun mavjud emas → chiqamiz

    # 📝 Foiz uchun ReportItem (yo‘q bo‘lsa yaratamiz)
    foiz_item = report_item_map.get(ordering_map["FOIZ"])
    if not foiz_item:
        foiz_item = ReportItem.objects.create(
            report=report,
            statement_column=foiz_col
        )
        report_item_map[ordering_map["FOIZ"]] = foiz_item

    # 🧠 Eski qiymatlar cache
    old_values = {
        inner.plant_id: normalize(inner.value)
        for inner in foiz_item.inners.all()
        if inner.plant_id
    }
    id_map = {
        inner.plant_id: inner.id
        for inner in foiz_item.inners.all()
        if inner.plant_id
    }

    # 📦 Yaratish va yangilash bufferlari
    create_buffer = []
    update_buffer = []

    for plant_id in plant_order:
        new_val = foiz_map.get(plant_id, Decimal("0"))
        old_val = old_values.get(plant_id)

        if old_val is None:
            create_buffer.append(ReportItemInner(
                report_item=foiz_item,
                plant_id=plant_id,
                value=str(new_val)
            ))
        elif old_val != new_val:
            update_buffer.append(ReportItemInner(
                id=id_map[plant_id],
                report_item=foiz_item,
                plant_id=plant_id,
                value=str(new_val)
            ))

    # 💾 Saqlaymiz
    if create_buffer:
        ReportItemInner.objects.bulk_create(create_buffer)

    if update_buffer:
        ReportItemInner.objects.bulk_update(update_buffer, ["value"])
