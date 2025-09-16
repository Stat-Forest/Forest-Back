from decimal import Decimal

from apps.reports.report_calculate.forest_create.heavy_neighborhood import normalize
from apps.reports.models import Report, ReportItem, ReportItemInner


def calculate_save_healthy(report: Report):
    """
    Sog'liqni saqlash muassasalariga ko‘chatlar yetkazib berish (1-ilova) uchun hisoblash:
    - 1.1.3.2.1 = 1.1.3.2.2 + 1.1.3.2.3
    - 1.1.3.3 = 1.1.3.2.1 / 1.1.3.1.1 (%)
    """

    ordering_list = [
        "1.1.3.2.1",  # Jami yong‘oq-mevalilar
        "1.1.3.2.2",  # Manzara
        "1.1.3.2.3",  # Mevali
        "1.1.3.1.1",  # Reja
        "1.1.3.3",    # Foiz
    ]

    # === Step 1: Barcha ustunlar va mapping ===
    columns = {
        col.ordering: col
        for col in report.statement.columns.all()
        if col.ordering in ordering_list
    }
    if len(columns) < len(ordering_list):
        return  # Ba'zilar yo‘q

    # === Step 2: Barcha mavjud ReportItem + Innerlarni oldindan yuklash ===
    report_items = (
        ReportItem.objects
        .filter(report=report, statement_column__ordering__in=ordering_list)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    item_map = {item.statement_column.ordering: item for item in report_items}
    item_inners_map = {
        item.statement_column.ordering: (
            item.inners.all()[0] if item.inners.all() else None
        )
        for item in report_items
    }

    # === Step 3: get_or_create helper ===
    def get_or_create_item(ordering):
        if ordering in item_map:
            return item_map[ordering]
        item = ReportItem.objects.create(
            report=report,
            statement_column=columns[ordering]
        )
        item_map[ordering] = item
        return item

    # === Step 4: Inner qiymat getter ===
    def get_value(ordering):
        inner = item_inners_map.get(ordering)
        return normalize(inner.value) if inner else Decimal(0)

    manzara = get_value("1.1.3.2.2")
    mevali = get_value("1.1.3.2.3")
    reja = get_value("1.1.3.1.1")

    jami = manzara + mevali
    foiz = (jami / reja * 100) if reja else None

    item_jami = get_or_create_item("1.1.3.2.1")
    item_foiz = get_or_create_item("1.1.3.3")

    # === Step 5: Eski inners tozalash (faqat kerakligilar) ===
    ReportItemInner.objects.filter(
        report_item__in=[item_jami, item_foiz]
    ).delete()

    # === Step 6: Yangi innerlar yaratish ===
    new_inners = [
        ReportItemInner(report_item=item_jami, value=jami),
        ReportItemInner(report_item=item_foiz, value=foiz),
    ]
    ReportItemInner.objects.bulk_create(new_inners)
