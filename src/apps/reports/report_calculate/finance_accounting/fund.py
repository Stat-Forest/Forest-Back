import re
from decimal import Decimal
from django.db import transaction
from apps.reports.models import (
    Statement, StatementColumn,
    Report, ReportItem, ReportItemInner
)


def create_report_with_jamg_calculation(statement_id: str, organization, deadline, user):
    """
    Yangi report yaratadi va Jamg‘arma bo‘yicha avtomatik hisob-kitob qiladi.
    """
    try:
        statement = Statement.objects.only("id").get(id=statement_id)
    except Statement.DoesNotExist:
        raise ValueError(f"Statement not found: {statement_id}")

    with transaction.atomic():
        report, _ = Report.objects.get_or_create(
            statement=statement,
            organization=organization,
            deadline=deadline,
            defaults={"created_by": user}
        )

        # Faqat yaproq (leaf) ustunlarni olamiz
        leaf_columns = StatementColumn.objects.filter(
            statement=statement,
            children__isnull=True
        ).only("id")

        # ReportItems yaratish (agar mavjud bo‘lmasa)
        existing_ids = set(
            ReportItem.objects.filter(report=report).values_list("statement_column_id", flat=True)
        )
        new_items = [
            ReportItem(report=report, statement_column=column)
            for column in leaf_columns if column.id not in existing_ids
        ]
        ReportItem.objects.bulk_create(new_items)

        # Yangi yaratilgan va eski mavjud itemlarni olish
        created_items = ReportItem.objects.filter(
            report=report
        ).select_related("statement_column").prefetch_related("inners")

        # Har biri uchun bitta inner (default 0) yaratish
        for item in created_items:
            if not item.inners.exists():
                ReportItemInner.objects.create(report_item=item, value=Decimal("0"))

        # Hisoblashni chaqiramiz
        calculate_jamg_statement(report)

    return report


def calculate_jamg_statement(report):
    """
    Jamg‘arma ustunlari bo‘yicha hisob-kitob.
    1) Har bir 'Jami tushum' → 'To‘lanishi kerak' → 'To‘landi' → 'Qoldiq' bloklarini hisoblaydi
    2) Yakunda Jamg‘arma bo‘yicha umumiy jami, tushishi kerak, to‘landi, qoldiq chiqaradi
    """
    items = (
        report.report_items
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    # ordering -> ReportItem map
    items_by_ordering = {item.statement_column.ordering: item for item in items}

    jami_tushum_total = Decimal("0")
    tolashi_kerak_total = Decimal("0")
    tolandi_total = Decimal("0")

    # Har bir ustun nomida (100%), (50%), (10%) bo‘lishi mumkin
    for item in items:
        title = item.statement_column.title.strip()
        ordering = item.statement_column.ordering

        # Jami tushum → To‘lanishi kerak → To‘landi → Qoldiq bloklarini aniqlash
        if "Jami tushum" in title and "%" in title:
            jami_inner = item.inners.first()
            jami_value = Decimal(jami_inner.value or 0)
            jami_tushum_total += jami_value

            # To‘lanishi kerak columnini topish
            percent = extract_percent(title)
            tolashi_kerak_val = (jami_value * percent) / Decimal("100")

            # Yozish
            tolashi_item = find_next_column(items_by_ordering, ordering, "To‘lanishi kerak")
            if tolashi_item:
                inner = tolashi_item.inners.first()
                inner.value = tolashi_kerak_val.quantize(Decimal("0.01"))
                inner.save()
                tolashi_kerak_total += tolashi_kerak_val

            # To‘landi va Qoldiq
            tolandi_item = find_next_column(items_by_ordering, ordering, "To‘landi")
            if tolandi_item:
                tolandi_val = Decimal(tolandi_item.inners.first().value or 0)
                tolandi_total += tolandi_val

                # Qoldiq = To‘lanishi kerak - To‘landi
                qoldiq_item = find_next_column(items_by_ordering, ordering, "Qoldiq")
                if qoldiq_item:
                    qoldiq_val = tolashi_kerak_val - tolandi_val
                    inner_qoldiq = qoldiq_item.inners.first()
                    inner_qoldiq.value = qoldiq_val.quantize(Decimal("0.01"))
                    inner_qoldiq.save()

    # Umumiy jamg‘arma bo‘yicha oxirgi satrni to‘ldirish
    fill_jamg_total(items_by_ordering, jami_tushum_total, tolashi_kerak_total, tolandi_total)


def fill_jamg_total(items_by_ordering, jami_tushum_total, tolashi_kerak_total, tolandi_total):
    """Oxiridagi umumiy Jamg‘arma satrlarini to‘ldiradi"""
    qoldiq_total = tolashi_kerak_total - tolandi_total

    set_inner_value(items_by_ordering, "Jamg‘arma jami tushum", jami_tushum_total)
    set_inner_value(items_by_ordering, "Jamg‘arma tushishi kerak", tolashi_kerak_total)
    set_inner_value(items_by_ordering, "Jamg‘arma to‘landi", tolandi_total)
    set_inner_value(items_by_ordering, "Jamg‘arma qoldiq", qoldiq_total)


def set_inner_value(items_by_ordering, title_contains, value):
    for item in items_by_ordering.values():
        if title_contains in item.statement_column.title:
            inner = item.inners.first()
            inner.value = Decimal(value).quantize(Decimal("0.01"))
            inner.save()
            break


def find_next_column(items_by_ordering, current_ordering, keyword):
    """
    Biror column’dan keyingi columnni topish (ordering bo‘yicha) va nomida keyword borligini tekshirish.
    """
    for item in items_by_ordering.values():
        if keyword in item.statement_column.title and \
           item.statement_column.ordering.startswith(current_ordering.rsplit(".", 1)[0]):
            return item
    return None


def extract_percent(text: str) -> Decimal:
    """
    Matndan `(20%)` kabi foizni ajratib oladi.
    """
    match = re.search(r"\((\d+(?:\.\d+)?)%\)", text)
    return Decimal(match.group(1)) if match else Decimal("0")
