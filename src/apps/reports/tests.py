# from decimal import Decimal
#
#
#
# def get_or_create_general_report(statement, deadline, region):
#     from apps.reports.models import Report
#
#     general_report, _ = Report.objects.get_or_create(
#         organization=None,
#         statement=statement,
#         deadline=deadline,
#         is_general=True,
#         is_republic=False,
#         region=region,
#         defaults={
#             "status": Report.StatusChoices.SAVED,
#             "is_report": False,
#         }
#     )
#
#     if general_report.sent_by_role in (None, "") and region:
#         general_report.sent_by_role = f"region:{region}"
#         general_report.save(update_fields=["sent_by_role"])
#
#     return general_report
#
#
# def get_or_create_national_report(statement, deadline, region=None):
#     from apps.reports.models import Report
#
#     national_report = Report.objects.filter(
#         statement=statement,
#         is_republic=True,
#         region=region,
#     ).first()
#
#     if not national_report:
#         national_report = Report.objects.create(
#             statement=statement,
#             is_republic=True,
#             region=region,
#             status=Report.StatusChoices.SAVED,
#             is_report=False,
#         )
#
#     if region:
#         national_report.sent_by_role = f"national:{region}"
#         national_report.save(update_fields=["sent_by_role"])
#
#     return national_report
#
#
# def normalize(value):
#     if value is None:
#         return Decimal(0)
#     try:
#         return Decimal(str(value))
#     except (ValueError, TypeError):
#         return Decimal(0)
#
#
# def aggregate_national_report(statement, deadline, region=None):
#     from collections import defaultdict
#     from apps.utils.services.is_that_number import safe_decimal
#     from apps.reports.models import Report, ReportItem, ReportItemInner
#
#     # 1️⃣ Viloyat Jami reportlarini olamiz (is_general=True)
#     general_reports = Report.objects.filter(
#         statement=statement,
#         deadline=deadline,
#         is_general=True,
#         status=Report.StatusChoices.SAVED
#     )
#
#     if not general_reports.exists():
#         print("❌ [REPUBLIC] Hech qanday Viloyat Jami topilmadi.")
#         return None
#
#     # 2️⃣ Respublika Jami reportini olamiz yoki yaratamiz
#     national_report = get_or_create_national_report(statement, deadline, region)
#     print(f"✅ [REPUBLIC] Report ID: {national_report.id}")
#
#     # 3️⃣ Eski item va innerlarni tozalaymiz
#     ReportItem.objects.filter(report=national_report).delete()
#
#     # 4️⃣ Barcha viloyat jami item va innerlarni olamiz
#     all_items = (
#         ReportItem.objects
#         .filter(report__in=general_reports)
#         .select_related("statement_column")
#         .prefetch_related("inners")
#     )
#
#     # 5️⃣ Aggregatsiya uchun tayyorgarlik
#     buffer_items = {}
#     buffer_inners = defaultdict(list)
#
#     for item in all_items:
#         col_id = item.statement_column_id
#         if col_id not in buffer_items:
#             buffer_items[col_id] = ReportItem(
#                 report=national_report,
#                 statement_column_id=col_id
#             )
#
#         for inner in item.inners.all():
#             key = (
#                 col_id,
#                 inner.plant_id,
#                 inner.organization_id,
#                 inner.text,
#                 inner.date
#             )
#             buffer_inners[key].append(inner.value)
#
#     # 6️⃣ Yaratamiz: ReportItem + ReportItemInner
#     created_items = ReportItem.objects.bulk_create(buffer_items.values())
#
#     col_id_to_item = {item.statement_column_id: item for item in created_items}
#
#     final_inners = []
#     for (col_id, plant_id, org_id, text, date), values in buffer_inners.items():
#         total = sum(safe_decimal(v) for v in values)
#         final_inners.append(ReportItemInner(
#             report_item=col_id_to_item[col_id],
#             plant_id=plant_id,
#             organization_id=org_id,
#             text=text,
#             date=date,
#             value=str(total)
#         ))
#
#     ReportItemInner.objects.bulk_create(final_inners)
#     print(f"📊 {len(final_inners)} ta inner yozildi (Respublika Jami).")
#
#     return national_report
#
#
#
# def aggregate_general_report(statement, deadline, region):
#     from decimal import Decimal
#     from collections import defaultdict
#     from apps.utils.services.is_that_number import safe_decimal
#     from apps.reports.models import Report, ReportItem, ReportItemInner
#
#     """
#     Viloyat Jami hisobotini yaratish va hisoblash.
#     Faqat ACCEPTED va individual jami hisobotlar (is_individual_general=True) dan hisoblanadi.
#     """
#     # 1. Reportni olish yoki yaratish
#     general_report = get_or_create_general_report(statement, deadline, region)
#
#     # 2. Eski itemlarni tozalash
#     ReportItem.objects.filter(report=general_report).delete()
#
#     # 3. Faqat kerakli reportlarni olish
#     regional_reports = Report.objects.filter(
#         statement=statement,
#         deadline=deadline,
#         region=region,
#         is_report=False,
#         is_individual_general=True,
#         is_general=False,
#         is_republic=False,
#         status=Report.StatusChoices.ACCEPTED
#     ).select_related("organization")
#
#     if not regional_reports.exists():
#         return general_report  # hech narsa qilish kerak emas
#
#     # 4. Tegishli ReportItem larni olish (barcha inners bilan birga)
#     all_items = (
#         ReportItem.objects
#         .filter(report__in=regional_reports)
#         .select_related("statement_column")
#         .prefetch_related("inners")
#     )
#
#     # 5. Aggregatsiya hisoblash
#     column_total_map = defaultdict(Decimal)
#     for item in all_items:
#         for inner in item.inners.all():
#             column_total_map[item.statement_column_id] += safe_decimal(inner.value)
#
#     if not column_total_map:
#         return general_report
#
#     # 6. Yangi ReportItem larni yaratish
#     report_item_buffer = []
#     for col_id in column_total_map.keys():
#         report_item_buffer.append(
#             ReportItem(
#                 report=general_report,
#                 statement_column_id=col_id
#             )
#         )
#     ReportItem.objects.bulk_create(report_item_buffer)
#
#     # 7. Yaratilgan ReportItemlarni olish
#     created_items = ReportItem.objects.filter(
#         report=general_report,
#         statement_column_id__in=column_total_map.keys()
#     )
#
#     # 8. Har bir item uchun value yozish
#     inner_buffer = []
#     for item in created_items:
#         value = column_total_map.get(item.statement_column_id, Decimal(0))
#         inner_buffer.append(
#             ReportItemInner(
#                 report_item=item,
#                 value=str(value)
#             )
#         )
#     ReportItemInner.objects.bulk_create(inner_buffer)
#
#     return general_report
