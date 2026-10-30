import os

from celery.schedules import crontab

# Celery konfiguratsiyasi
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://forest_redis:6379/0')  # Broker URL (masalan Redis)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://forest_redis:6379/0')  # Natija saqlash joyi (Redis)
CELERY_TASK_SERIALIZER = os.getenv('CELERY_TASK_SERIALIZER', 'json')  # Vazifalarni serializatsiya qilish format
CELERY_RESULT_SERIALIZER = os.getenv('CELERY_RESULT_SERIALIZER', 'json')  # Natijalarni serializatsiya qilish format
CELERY_TASK_TRACK_STARTED = os.getenv('CELERY_TASK_TRACK_STARTED', True)  # Vazifa boshlanishini kuzatish
CELERY_TIMEZONE = os.getenv('CELERY_TIMEZONE') or 'Asia/Tashkent'  # crontab soatlari shu zonada (TIME_ZONE bilan bir xil)
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = os.getenv('CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP', True)  # Brokerga ulanganda qayta urinib ko‘rish

# Testlarda (manage.py test) va CELERY_TASK_ALWAYS_EAGER=True bo'lsa tasklar
# worker'siz, shu jarayonda darhol bajariladi.
import sys as _sys
CELERY_TASK_ALWAYS_EAGER = (
    os.getenv('CELERY_TASK_ALWAYS_EAGER', 'False') == 'True'
    or (len(_sys.argv) > 1 and _sys.argv[1] == 'test')
)
CELERY_TASK_EAGER_PROPAGATES = True

# Davriy vazifalar (forest_celery_beat konteyneri).
# Kunlik vazifalar crontab bilan: beat konteyneri har deploy'da qayta yaratiladi va jadval faylini
# yo'qotadi — 24 soatlik interval har safar boshidan sanalib, tez-tez deploy'da vazifa umuman ishlamas edi.
CELERY_BEAT_SCHEDULE = {
    "billing-mib-push-retry": {
        "task": "billing.mib_push_retry_failed",
        "schedule": 15 * 60,
    },
    # Eski MIB loglaridagi ijarachi PII'sini maskalash (kuniga bir marta)
    "billing-mib-push-log-redact": {
        "task": "billing.mib_push_log_redact",
        "schedule": crontab(hour=3, minute=45),
    },
    # simplejwt: muddati o'tgan Outstanding/Blacklisted tokenlar jadvali cheksiz o'smasin
    "auth-flush-expired-tokens": {
        "task": "authentications.flush_expired_tokens",
        "schedule": crontab(hour=4, minute=0),
    },
    # Yashil mahalla: 3/10 ish kuni eslatmalari va muddat buzilishi (har kuni ertalab)
    "yashil-deadline-reminders": {
        "task": "yashil.deadline_reminders",
        "schedule": crontab(hour=8, minute=0),
    },
    # Yashil mahalla: tungi solishtirish — ombor/qabul/akt yaxlitligi (TZ 22.3)
    "yashil-reconcile": {
        "task": "yashil.reconcile",
        "schedule": crontab(hour=2, minute=30),
    },
    # Yashil mahalla: muddati o'tgan eksport fayllarini o'chirish (TZ 14.2, 7 kun)
    "yashil-export-cleanup": {
        "task": "yashil.export_cleanup",
        "schedule": crontab(hour=3, minute=15),
    },
}
