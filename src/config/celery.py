from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Django sozlamalarini o‘rnatish
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Celery ilovasini yaratish
app = Celery('forest_app')

# Django'ni Celery uchun konfiguratsiya qilish
app.config_from_object('django.conf:settings', namespace='CELERY')

# Celery taskslarini import qilish
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    # ======== Debug task to verify Celery is working ========
    print(f'Request: {self.request!r}')


# from celery.schedules import crontab
#
# app.conf.beat_schedule = {
#     "update-statement-columns-every-month": {
#         "task": "apps.reports.tasks.employee_report.update_date_employee_report.update_year_in_statement_columns",
#         "schedule": crontab(minute=0, hour=0, day_of_month=1),
#     },
#     "update-monthly-statement-columns": {
#         "task": "apps.reports.tasks.employee_report.update_monthly_employee_reports.update_monthly_statement_columns",
#         "schedule": crontab(minute=0, hour=0, day_of_month=1)
#     },
#     "update-tushum-statement-columns-task": {
#         "task": "apps.reports.tasks.employee_report.fund.update_tushum_statement_columns_task",
#         "schedule": crontab(minute=5, hour=0, day_of_month="1,9,17,24"),
#     },
# }