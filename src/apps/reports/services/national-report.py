# from collections import defaultdict
#
# from apps.reports.models import Report, ReportItem, ReportItemInner
# from apps.utils.services.is_that_number import is_number
#
#
# def aggregate_national_report(statement, deadline, organization, region):
#     from apps.reports.models import Report, ReportItem, ReportItemInner
#
#     general_reports = Report.objects.filter(
#         statement=statement,
#         deadline=deadline,
#         is_general=True,
#         status=Report.StatusChoices.ACCEPTED
#     )
#
#     if not general_reports.exists():
#         return None
#
#     national_report, _ = Report.objects.get_or_create(
#         statement=statement,
#         deadline=deadline,
#         is_general=True,
#         organization=organization,
#         region=region,
#         defaults={
#             "status": Report.StatusChoices.SAVED
#         }
#     )
#
#     ReportItem.objects.filter(region=national_report).delete()
#
#     all_items = ReportItem.objects.filter(report__in=general_reports).prefetch_related("inners")
#
#     grouped = defaultdict(list)
#     for item in all_items:
#         for inner in item.inners.all():
#             grouped[item.statement_column_id].append(inner.value)
#
#     new_items = []
#     new_inners = []
#
#     for column_id, values in grouped.items():
#         first_value = values[0] if values else None
#
#         report_item = ReportItem(
#             report=national_report,
#             statement_column_id=column_id
#         )
#         new_items.append(report_item)
#
#         if is_number(first_value):
#             total = sum(float(v) for v in values if is_number(v))
#             new_inners.append(
#                 ReportItemInner(report_item=report_item, value=str(total))
#             )
#         else:
#             for v in values:
#                 new_inners.append(
#                     ReportItemInner(report_item=report_item, value=v)
#                 )
#
#     ReportItem.objects.bulk_create(new_items)
#     ReportItemInner.objects.bulk_create(new_inners)
#
#     return national_report