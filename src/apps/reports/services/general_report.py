from decimal import Decimal



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
    from collections import defaultdict
    from apps.utils.services.is_that_number import safe_decimal
    from apps.reports.report_calculate import ALL_CALCULATORS

    # === 1. Barcha regional Jami (is_general=True) reportlarni olish ===
    general_reports = Report.objects.filter(
        statement=statement,
        deadline=deadline,
        is_general=True,
        status=Report.StatusChoices.SAVED
    )

    if not general_reports.exists():
        print(">>> [REPUBLIC] Hech qanday regional Jami yo‘q")
        return None

    # === 2. Respublika Jami reportini olish yoki yaratish ===
    national_report, _ = Report.objects.get_or_create(
        statement=statement,
        deadline=deadline,
        is_republic=True,
        region=region,
        defaults={"status": Report.StatusChoices.SAVED, "is_report": False}
    )

    print(">>> [REPUBLIC] Umumiy Jami report:", national_report.id)

    # === 3. Eski itemlarni tozalash ===
    ReportItem.objects.filter(report=national_report).delete()

    # === 4. Barcha regional itemlarni olish ===
    all_items = (
        ReportItem.objects
        .filter(report__in=general_reports)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    # === 5. Column_id -> values[] qilib guruhlash ===
    grouped = defaultdict(list)
    for item in all_items:
        col_id = item.statement_column_id
        for inner in item.inners.all():
            grouped[col_id].append(inner.value)

    # === 6. Yangi ReportItem lar yaratish ===
    new_items = {}
    for column_id in grouped.keys():
        new_items[column_id] = ReportItem.objects.create(
            report=national_report,
            statement_column_id=column_id
        )

    # === 7. Yangi innerlarni yaratish ===
    new_inners = []
    for column_id, values in grouped.items():
        total = sum(safe_decimal(v) for v in values)
        new_inners.append(
            ReportItemInner(
                report_item=new_items[column_id],
                value=str(total)
            )
        )

    ReportItemInner.objects.bulk_create(new_inners)

    print(f">>> [REPUBLIC] {len(new_items)} ta item, {len(new_inners)} ta inner yozildi")

    # === 8. FOIZ / umumiy hisob-kitobni qayta ishga tushirish ===
    calculate_fn = ALL_CALCULATORS.get(statement.name_uz)
    if calculate_fn:
        calculate_fn(national_report)

    return national_report


def aggregate_general_report(statement, deadline, region):
    from collections import defaultdict
    from decimal import Decimal
    from apps.reports.report_calculate import ALL_CALCULATORS
    from apps.utils.services.is_that_number import safe_decimal
    from apps.reports.models import Report, ReportItem, ReportItemInner

    reports = Report.objects.filter(
        statement=statement,
        deadline=deadline,
        is_general=False,
        is_individual_general=True,
        is_report=False,
    ).select_related("organization__republic")

    if not reports.exists():
        return None

    # Region bo‘yicha to‘g‘rilash — faqat shu regiondagilar
    regional_reports = [r for r in reports if r.region == region]
    if not regional_reports:
        return None

    # Target region va republic
    target_region = region
    republics = {r.republic for r in regional_reports if r.republic}
    target_republic = republics.pop() if len(republics) == 1 else None

    general_report, created = Report.objects.get_or_create(
        organization=None,
        statement=statement,
        deadline=deadline,
        is_general=True,
        region=target_region,
        defaults={
            "status": Report.StatusChoices.SAVED,
            "is_report": False,
            "republic": target_republic
        }
    )

    if not created and general_report.republic != target_republic:
        general_report.republic = target_republic
        general_report.save(update_fields=["republic"])

    general_report.refresh_from_db()

    # Eski ReportItem’larni tozalash
    ReportItem.objects.filter(report=general_report).delete()

    # Jami hisoblash
    all_items = ReportItem.objects.filter(
        report__in=regional_reports
    ).select_related("statement_column").prefetch_related("inners")

    column_total_map = defaultdict(Decimal)
    touched_column_ids = set()

    for item in all_items:
        col_id = item.statement_column_id
        touched_column_ids.add(col_id)
        for inner in item.inners.all():
            column_total_map[col_id] += safe_decimal(inner.value)

    # Yangi ReportItem lar
    new_items = [
        ReportItem(report=general_report, statement_column_id=col_id)
        for col_id in touched_column_ids
    ]
    ReportItem.objects.bulk_create(new_items)

    created_items = ReportItem.objects.filter(
        report=general_report,
        statement_column_id__in=touched_column_ids
    )

    # Innerlarni yaratish
    all_inners = [
        ReportItemInner(
            report_item=item,
            value=str(column_total_map.get(item.statement_column_id, Decimal(0)))
        )
        for item in created_items
    ]
    ReportItemInner.objects.bulk_create(all_inners)

    # Hisoblash funksiyasi
    calculate_fn = ALL_CALCULATORS.get(statement.name_uz)
    if calculate_fn:
        calculate_fn(general_report)

    return general_report