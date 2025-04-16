# from django.db.models.signals import post_save, pre_save
# from django.dispatch import receiver
#
# from apps.reports.models import Report, AllReport
# from apps.utils.services import ReportType, AllReportType
#
#
# @receiver((post_save, pre_save), sender=Report)
# def report_post_save_pre_save(instance, created, **kwargs):
#     if instance.status == ReportType.UNSAVED:
#         unsaved_report , _= AllReport.objects.get_or_create(title=AllReportType.HABARNOMALAR)
#         if not _ :
#             unsaved_report.count = Report.objects.filter(id=instance.pk).count()
#             unsaved_report.save()
