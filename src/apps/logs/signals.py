# apps/logs/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.utils import timezone

from .middleware import get_current_user
from apps.logs.models import HistoryActionJournal

# Log yozilishi kerak bo‘lgan modellarning ro‘yxati
ALLOWED_MODELS = [
    "Backup",
    "Announcement",
    "Report",
    "LandDocument",
    "Notification",
    "Organization",
    "CustomUser",
    "Deadline",
    "Statement",
    "Plan",
    "Handbook",
]


def _create_log(user, action, model_name, instance=None, message=None):
    """Log yozish uchun umumiy yordamchi funksiya"""
    if not user or not getattr(user, "is_authenticated", False):
        return

    try:
        object_repr = str(instance) if instance else ""
    except Exception:
        object_repr = f"ID={getattr(instance, 'id', '---')}"

    HistoryActionJournal.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(getattr(instance, "id", "")),
        object_repr=object_repr,
        change_message=message or "",
        created_at=timezone.now(),
    )


@receiver(post_save)
def log_create_or_update(sender, instance, created, **kwargs):
    model_name = sender.__name__
    if model_name not in ALLOWED_MODELS:
        return

    user = getattr(instance, "_history_user", None) or get_current_user()

    action = "add" if created else "change"
    message = f"{model_name} {'yaratildi' if created else 'yangilandi'}."

    _create_log(user, action, model_name, instance, message)


@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    model_name = sender.__name__
    if model_name not in ALLOWED_MODELS:
        return

    user = getattr(instance, "_history_user", None) or get_current_user()

    message = f"{model_name} o‘chirildi."
    _create_log(user, "delete", model_name, instance, message)


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    _create_log(user, "login", "User", message="Foydalanuvchi tizimga kirdi.")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    _create_log(user, "logout", "User", message="Foydalanuvchi tizimdan chiqdi.")
