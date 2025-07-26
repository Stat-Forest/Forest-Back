import json, re
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


def is_number(value: str) -> bool:
    if value is None:
        return False
    return re.match(r'^\d+(\.\d+)?$', str(value)) is not None


def aggregate_general_report(statement, deadline):
    # 1️⃣ Oddiy (general emas) reportlarni olamiz
    reports = Report.objects.filter(
        statement=statement,
        deadline=deadline,
        is_general=False
    )

    # 2️⃣ Barcha report_items
    all_items = ReportItem.objects.filter(report__in=reports).prefetch_related("inners")

    # 3️⃣ General reportni olish yoki yaratish
    general_report = get_or_create_general_report(statement, deadline)
    ReportItem.objects.filter(report=general_report).delete()

    # 4️⃣ Column bo‘yicha guruhlash
    from collections import defaultdict
    grouped = defaultdict(list)
    for item in all_items:
        for inner in item.inners.all():
            grouped[item.statement_column_id].append(inner.value)

    new_items = []
    new_inners = []

    for column_id, values in grouped.items():
        # birinchi qiymatni tekshiramiz → raqammi yoki matn
        first_value = values[0] if values else None

        report_item = ReportItem(
            report=general_report,
            statement_column_id=column_id
        )
        new_items.append(report_item)

        if is_number(first_value):
            # 🔢 Agar raqam bo‘lsa → hammasini yig‘indiga aylantiramiz
            total = sum(float(v) for v in values if is_number(v))
            new_inners.append(ReportItemInner(
                report_item=report_item,
                value=str(total)
            ))
        else:
            # 🔤 Agar matn bo‘lsa → har bir qiymatni alohida inner sifatida qo‘shamiz
            for v in values:
                new_inners.append(
                    ReportItemInner(
                        report_item=report_item,
                        value=v
                    )
                )

    # 5️⃣ Bulk yaratish
    ReportItem.objects.bulk_create(new_items)
    ReportItemInner.objects.bulk_create(new_inners)

    return general_report



{
  "deadline": "34257f28-10e9-4810-b03e-a4d72259f921",
  "report_items": [
    {
      "statement_column": "b57bfc34-753c-42cf-b96b-5cbb672e5fc2",
      "inners": [
        { "value": "db1e6111-9791-4ddc-b421-806fbe0f89fb" }
      ]
    },
    {
      "statement_column": "ea2d27d2-4949-45d9-b3ba-9b4b8b3c7f6e",
      "inners": [
        { "value": "Bagryanik" },
        { "value": "Lotos" },
        { "value": "Atirgul" },
        { "value": "Jiyda" },
        { "value": "Nimadur yana gul" }
      ]
    },
    {
      "statement_column": "a7f822a6-354a-41ad-b420-4b01a1b61c12",
      "inners": [
        { "value": "mol" },
        { "value": "qoy" },
        { "value": "ochki" },
        { "value": "telefon" },
        { "value": "Davlat" },
        { "value": "Iphone" }
      ]
    },
    {
      "statement_column": "79a7d447-1547-4c3a-a2a1-80abe0c52426",
      "inners": [
        { "value": "db1e6111-9791-4ddc-b421-806fbe0f89fb" }
      ]
    },
    {
      "statement_column": "101156ec-4c6c-4e42-8607-adebe4b014e3",
      "inners": [
        { "value": "11" },
        { "value": "22" },
        { "value": "33" }
      ]
    },
    {
      "statement_column": "30e8e34b-5572-4d2f-9c6a-156bbf689d02",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    }
  ]
}
