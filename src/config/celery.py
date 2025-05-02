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