"""Kunlik davriy vazifalar soat bo'yicha (crontab): beat konteyneri har deploy'da qayta yaratiladi va
24 soatlik interval hisobini yo'qotadi — interval bilan kunlik vazifa deploy'dan 24 soat o'tmaguncha ishlamaydi."""
from celery.schedules import crontab
from django.conf import settings
from django.test import SimpleTestCase


class BeatScheduleTest(SimpleTestCase):
    def test_daily_tasks_use_wall_clock_schedule(self):
        for name, entry in settings.CELERY_BEAT_SCHEDULE.items():
            schedule = entry["schedule"]
            seconds = schedule if isinstance(schedule, (int, float)) else None
            with self.subTest(name=name):
                self.assertFalse(seconds is not None and seconds >= 6 * 3600,
                                 f"{name}: uzun interval soniyada — crontab ishlating")

    def test_yashil_tasks_run_at_night_or_morning(self):
        by_task = {e["task"]: e["schedule"] for e in settings.CELERY_BEAT_SCHEDULE.values()}
        for task in ("yashil.deadline_reminders", "yashil.reconcile", "yashil.export_cleanup"):
            with self.subTest(task=task):
                self.assertIsInstance(by_task[task], crontab)

    def test_celery_uses_project_timezone(self):
        self.assertEqual(settings.CELERY_TIMEZONE or settings.TIME_ZONE, settings.TIME_ZONE)
        self.assertTrue(settings.CELERY_TIMEZONE)
