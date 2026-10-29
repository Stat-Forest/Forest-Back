"""Modul sozlamalari — `settings.YASHIL_*` bo'lsa o'sha, bo'lmasa standart qiymat."""
from django.conf import settings

DEFAULTS = {
    "YASHIL_EXPORT_SYNC_LIMIT": 2000,     # shuncha qatorgacha eksport so'rov ichida tayyorlanadi, kattasi Celery'da
    "YASHIL_EXPORT_PDF_LIMIT": 5000,      # PDF hisobot uchun qatorlar chegarasi (xotira)
    "YASHIL_EXPORT_MAX_ACTIVE": 3,        # bir foydalanuvchida bir vaqtda faol eksportlar
    "YASHIL_EXPORT_RETENTION_DAYS": 7,    # tayyor fayl shuncha kun saqlanadi
    "YASHIL_EXPORT_CHUNK": 1000,          # DB'dan o'qish bo'lagi
}


def get(name: str):
    return getattr(settings, name, DEFAULTS[name])
