from collections import defaultdict
from decimal import Decimal

from apps.utils.services.is_that_number import is_number


def get_or_create_general_report(statement, deadline, region=None):
    from apps.reports.models import Report

    general_report, _ = Report.objects.get_or_create(
        organization=None,
        statement=statement,
        deadline=deadline,
        defaults={
            "status": Report.StatusChoices.SAVED,
            "is_general": True
        }
    )

    if region:
        # General reportga hududiy belgini saqlash (optional)
        general_report.sent_by_role = f"region:{region}"
        general_report.save(update_fields=["sent_by_role"])

    return general_report



def normalize(value):
    if value is None:
        return Decimal(0)
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return Decimal(0)


def aggregate_national_report(statement, deadline, region):
    from apps.reports.models import Report, ReportItem, ReportItemInner

    general_reports = Report.objects.filter(
        statement=statement,
        deadline=deadline,
        is_general=True,
        status=Report.StatusChoices.SAVED
    )

    if not general_reports.exists():
        print(">>> [REPUBLIC] Hech qanday regional Jami yo‘q")
        return None

    national_report, _ = Report.objects.get_or_create(
        statement=statement,
        deadline=deadline,
        is_republic=True,
        region=region,
        defaults={"status": Report.StatusChoices.SAVED}
    )

    print(">>> [REPUBLIC] Umumiy Jami report:", national_report.id)

    # Tozalash
    ReportItem.objects.filter(report=national_report).delete()

    # Regional jami reportlardagi barcha itemlar
    all_items = ReportItem.objects.filter(report__in=general_reports).prefetch_related("inners")

    # Guruhlash – faqat unique bo‘lishi uchun dict orqali
    grouped = defaultdict(list)
    for item in all_items:
        col_id = item.statement_column_id
        for inner in item.inners.all():
            value = inner.value
            grouped[col_id].append(value)

    # 1. ReportItem yaratish
    new_items = {}
    for column_id in grouped.keys():
        report_item = ReportItem.objects.create(
            report=national_report,
            statement_column_id=column_id
        )
        new_items[column_id] = report_item

    # 2. ReportItemInner yaratish
    new_inners = []
    for column_id, values in grouped.items():
        report_item = new_items[column_id]
        first_value = values[0] if values else None

        if is_number(first_value):
            total = sum(normalize(v) for v in values if is_number(v))
            new_inners.append(ReportItemInner(report_item=report_item, value=str(total)))
        else:
            # 🔥 faqat 1 dona yozish uchun SET ishlatamiz
            unique_values = list(dict.fromkeys(values))  # preserves order
            for val in unique_values:
                new_inners.append(ReportItemInner(report_item=report_item, value=val))

    ReportItemInner.objects.bulk_create(new_inners)
    print(f">>> [REPUBLIC] {len(new_items)} ta item, {len(new_inners)} ta inner yozildi")
    return national_report


def aggregate_general_report(statement, deadline, region):
    from apps.reports.models import Report, ReportItem, ReportItemInner
    from collections import defaultdict
    from decimal import Decimal

    reports = Report.objects.filter(
        statement=statement,
        deadline=deadline,
        is_general=False,
        is_individual_general=True,
        is_report=False,
        region=region
    ).select_related("organization__republic")

    if not reports.exists():
        return None

    regions = {r.organization.region for r in reports if r.organization and r.organization.region}
    republics = {r.organization.republic for r in reports if r.organization and r.organization.republic}

    target_region = regions.pop() if len(regions) == 1 else region
    target_republic = republics.pop() if len(republics) == 1 else None

    all_items = ReportItem.objects.filter(
        report__in=reports
    ).select_related("statement_column").prefetch_related("inners")

    # ⚠️ Muammoni oldini olish: avval aniq mavjud reportni topamiz
    general_report = Report.objects.filter(
        organization=None,
        statement=statement,
        deadline=deadline,
        is_general=True,
        region=target_region
    ).first()

    if general_report is None:
        general_report = Report.objects.create(
            organization=None,
            statement=statement,
            deadline=deadline,
            is_general=True,
            status=Report.StatusChoices.SAVED,
            is_report=False,
            region=target_region,
            republic=target_republic
        )
    else:
        # Agar mavjud bo‘lsa, faqat republic yangilanadi
        changed = False
        if general_report.republic != target_republic:
            general_report.republic = target_republic
            changed = True
        if changed:
            general_report.save(update_fields=["republic"])

    # Eski itemlarni tozalaymiz
    ReportItem.objects.filter(report=general_report).delete()

    # Ustunlar bo‘yicha yig‘ish
    column_total_map = defaultdict(Decimal)
    touched_column_ids = set()

    for item in all_items:
        col_id = item.statement_column_id
        touched_column_ids.add(col_id)
        for inner in item.inners.all():
            if is_number(inner.value):
                column_total_map[col_id] += Decimal(inner.value)

    new_items = []
    new_inners = []

    for col_id in touched_column_ids:
        item = ReportItem(report=general_report, statement_column_id=col_id)
        new_items.append(item)

    ReportItem.objects.bulk_create(new_items)

    for item in new_items:
        col_id = item.statement_column_id
        total = column_total_map.get(col_id, Decimal(0))
        new_inners.append(ReportItemInner(report_item=item, value=str(total)))

    ReportItemInner.objects.bulk_create(new_inners)

    return general_report