import re

from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn


def get_or_create_general_report(statement, deadline, region=None):
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
    ).select_related("organization__republic")

    if not reports.exists():
        return None

    # 2️⃣ Region va Republicni yig‘amiz
    regions = set()
    republics = set()
    for r in reports:
        if r.organization:
            regions.add(r.organization.region)
            if r.organization.republic:
                republics.add(r.organization.republic)

    # ✅ Bitta viloyat bo‘lsa → region
    target_region = regions.pop() if len(regions) == 1 else None

    # ✅ Bitta respublika bo‘lsa → republic
    target_republic = republics.pop() if len(republics) == 1 else None

    # 3️⃣ Barcha report_items
    all_items = ReportItem.objects.filter(report__in=reports).prefetch_related("inners")

    # 4️⃣ General reportni olish yoki yaratish
    general_report, created = Report.objects.get_or_create(
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

    # ✅ Eski general reportda region yoki republic o‘zgarsa → yangilaymiz
    changed = False
    if general_report.region != target_region:
        general_report.region = target_region
        changed = True
    if general_report.republic != target_republic:
        general_report.republic = target_republic
        changed = True
    if changed:
        general_report.save(update_fields=["region", "republic"])

    # ✅ Eski itemlarni tozalaymiz
    ReportItem.objects.filter(report=general_report).delete()

    # 5️⃣ Column bo‘yicha guruhlash
    from collections import defaultdict
    grouped = defaultdict(list)
    for item in all_items:
        for inner in item.inners.all():
            grouped[item.statement_column_id].append(inner.value)

    new_items = []
    new_inners = []

    for column_id, values in grouped.items():
        first_value = values[0] if values else None

        report_item = ReportItem(
            report=general_report,
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

    # 6️⃣ Bulk yaratish
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
