import json
from django.db.models import Sum, DecimalField
from django.db.models.functions import Cast

from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn


def get_or_create_general_report(statement, deadline):
    general_report, _ = Report.objects.get_or_create(
        organization=None,
        statement=statement,
        deadline=deadline,
        defaults={
            "status": Report.StatusChoices.SAVED,
            "is_general": True
        }
    )
    return general_report


def aggregate_general_report(statement, deadline):
    # 1️⃣ Oddiy (general emas) reportlarni olamiz
    reports = Report.objects.filter(
        statement=statement,
        deadline=deadline,
        is_general=False
    )

    # 2️⃣ Tashkilotlar ro‘yxatini yig‘amiz (har doim JSON saqlash uchun)
    org_qs = reports.values("organization_id", "organization__name")
    org_list = [
        {"id": str(o["organization_id"]), "name": o["organization__name"] or ""}
        for o in org_qs.distinct()
    ]

    # 3️⃣ Faqat raqamli ustunlarni olamiz
    numeric_columns = StatementColumn.objects.filter(
        statement=statement,
        is_organization=False
    ).values_list("id", flat=True)

    all_items = ReportItem.objects.filter(
        report__in=reports,
        statement_column_id__in=numeric_columns
    )

    # 4️⃣ Barcha ustunlar bo‘yicha yig‘indi hisoblaymiz
    aggregated = (
        all_items.values("statement_column")
        .annotate(
            total=Sum(
                Cast("inners__value", output_field=DecimalField(max_digits=20, decimal_places=2))
            )
        )
    )

    # 5️⃣ General reportni olish yoki yaratish
    general_report = get_or_create_general_report(statement, deadline)

    # Eski itemlarni tozalaymiz
    ReportItem.objects.filter(report=general_report).delete()

    # 6️⃣ Raqamli ustunlarni qo‘shamiz
    new_items = []
    new_inners = []

    for row in aggregated:
        col_id = row["statement_column"]
        total_value = row["total"] or 0

        report_item = ReportItem(
            report=general_report,
            statement_column_id=col_id
        )
        new_items.append(report_item)

        new_inners.append(
            ReportItemInner(
                report_item=report_item,
                value=str(total_value)
            )
        )

    ReportItem.objects.bulk_create(new_items)
    ReportItemInner.objects.bulk_create(new_inners)

    # 7️⃣ Endi **Tashkilot nomi column** uchun JSON saqlaymiz
    org_column = StatementColumn.objects.filter(
        statement=statement,
        is_organization=True
    ).first()
    if org_column:
        # Bitta ReportItem yaratamiz
        org_item = ReportItem.objects.create(
            report=general_report,
            statement_column=org_column
        )
        # ✅ Tashkilotlar ro‘yxatini JSON qilib saqlaymiz
        ReportItemInner.objects.create(
            report_item=org_item,
            value=json.dumps(org_list, ensure_ascii=False)  # UTF-8 ni yo‘qotmaslik uchun
        )

    return general_report

# 1️⃣ Shu statement + deadline bo‘yicha barcha tashkilot reportlarini yig‘amiz
# 2️⃣ Shu reportlardagi barcha ReportItemlarni yig‘amiz
# 3️⃣ Column bo‘yicha sum qilamiz
# 4️⃣ General reportni olish yoki yaratish
# 5️⃣ Eski general ReportItemlarni tozalash
# 6️⃣ Yangi general itemlarni yaratamiz
# 7️⃣ Har bir itemga 1ta inner (summa) yozamiz
