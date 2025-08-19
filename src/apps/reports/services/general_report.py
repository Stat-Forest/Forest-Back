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


def aggregate_national_report(statement, deadline, organization, region):
    from apps.reports.models import Report, ReportItem, ReportItemInner

    general_reports = Report.objects.filter(
        statement=statement,
        deadline=deadline,
        is_general=True,
        status=Report.StatusChoices.ACCEPTED
    )

    if not general_reports.exists():
        return None

    national_report, _ = Report.objects.get_or_create(
        statement=statement,
        deadline=deadline,
        is_general=True,
        organization=organization,
        region=region,
        defaults={
            "status": Report.StatusChoices.SAVED
        }
    )

    ReportItem.objects.filter(report=national_report).delete()

    all_items = ReportItem.objects.filter(report__in=general_reports).prefetch_related("inners")

    grouped = defaultdict(list)
    for item in all_items:
        for inner in item.inners.all():
            grouped[item.statement_column_id].append(inner.value)

    new_items = []
    new_inners = []

    for column_id, values in grouped.items():
        first_value = values[0] if values else None

        report_item = ReportItem(
            report=national_report,
            statement_column_id=column_id
        )
        new_items.append(report_item)

        if is_number(first_value):
            total = sum(float(v) for v in values if is_number(v))
            new_inners.append(
                ReportItemInner(report_item=report_item, value=str(total))
            )
        else:
            for v in values:
                new_inners.append(
                    ReportItemInner(report_item=report_item, value=v)
                )

    ReportItem.objects.bulk_create(new_items)
    ReportItemInner.objects.bulk_create(new_inners)

    return national_report


def aggregate_general_report(statement, deadline):
    from apps.reports.models import Report, ReportItem, ReportItemInner

    reports = Report.objects.filter(
        statement=statement,
        deadline=deadline,
        is_general=False
    ).select_related("organization__republic")

    if not reports.exists():
        return None

    regions = {r.organization.region for r in reports if r.organization and r.organization.region}
    republics = {r.organization.republic for r in reports if r.organization and r.organization.republic}

    target_region = regions.pop() if len(regions) == 1 else None
    target_republic = republics.pop() if len(republics) == 1 else None

    all_items = ReportItem.objects.filter(report__in=reports).select_related("statement_column").prefetch_related("inners")

    # Jami reportni topamiz yoki yaratamiz
    general_report, _ = Report.objects.get_or_create(
        organization=None,
        statement=statement,
        deadline=deadline,
        defaults={
            "status": Report.StatusChoices.SAVED,
            "is_general": True,
            "region": target_region,
            "republic": target_republic
        }
    )

    # Region yoki Republic yangilanishi kerak bo‘lsa
    changed = False
    if general_report.region != target_region:
        general_report.region = target_region
        changed = True
    if general_report.republic != target_republic:
        general_report.republic = target_republic
        changed = True
    if changed:
        general_report.save(update_fields=["region", "republic"])

    # Avvalgi itemlarni o‘chiramiz
    ReportItem.objects.filter(report=general_report).delete()

    # ✅ Column bo‘yicha barcha `value`larni yig‘amiz
    column_values_map = defaultdict(list)
    for item in all_items:
        for inner in item.inners.all():
            column_values_map[item.statement_column_id].append(inner.value)

    # Yangi ReportItem va ReportItemInner larni yaratamiz
    new_items = []
    new_inners = []

    for column_id, values in column_values_map.items():
        report_item = ReportItem(
            report=general_report,
            statement_column_id=column_id
        )
        new_items.append(report_item)

        # 🔢 Agar son bo‘lsa — jamlab qo‘shamiz
        numeric_values = [Decimal(v) for v in values if is_number(v)]
        if numeric_values:
            summed_value = str(sum(numeric_values))
            new_inners.append(ReportItemInner(
                report_item=report_item,
                value=summed_value
            ))
        else:
            # Agar son emas — 1-marta kelganini saqlaymiz (masalan: "Tashkilot nomi")
            new_inners.append(ReportItemInner(
                report_item=report_item,
                value=values[0] if values else ""
            ))

    # Bulk yaratish
    ReportItem.objects.bulk_create(new_items, batch_size=1000)
    ReportItemInner.objects.bulk_create(new_inners, batch_size=2000)

    # Umumrespublika jamini hisoblash
    if Report.objects.filter(
        statement=statement,
        deadline=deadline,
        is_general=True,
        status=Report.StatusChoices.ACCEPTED
    ).exists():
        pass # last TODO: umumiyrespublika logikasi
    return general_report