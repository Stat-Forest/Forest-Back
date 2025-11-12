from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from .middleware import get_current_user
from apps.logs.models import HistoryActionJournal

# ✅ Faqat shu modellar uchun log yoziladi
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
    # "StatementColumn",
]

# --- Yordamchi funksiya ---
def _create_log(user, action, model_name, instance=None, message=None):
    """Harakat logini yaratish uchun umumiy yordamchi funksiya"""
    if not user or not user.is_authenticated:
        return

    HistoryActionJournal.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=getattr(instance, 'id', None),
        object_repr=getattr(instance, '__str__', lambda: f"ID={getattr(instance, 'id', '---')}")(),
        change_message=message or "",
    )


# --- Post Save (yaratish yoki yangilash) ---
@receiver(post_save)
def log_create_or_update(sender, instance, created, **kwargs):
    model_name = sender.__name__
    if model_name not in ALLOWED_MODELS:
        return  # boshqa modellarniki yozilmaydi

    user = getattr(instance, '_history_user', None) or get_current_user()
    action = 'add' if created else 'change'
    message = f"{model_name} {'yaratildi' if created else 'yangilandi'}."
    _create_log(user, action, model_name, instance, message)

# --- Post Delete ---
@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    model_name = sender.__name__
    if model_name not in ALLOWED_MODELS:
        return

    user = getattr(instance, '_history_user', None) or get_current_user()
    message = f"{model_name} o‘chirildi."
    _create_log(user, 'delete', model_name, instance, message)

# --- Foydalanuvchi login ---
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    _create_log(user, 'login', 'User', message='Foydalanuvchi tizimga kirdi.')

# --- Foydalanuvchi logout ---
@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    _create_log(user, 'logout', 'User', message='Foydalanuvchi tizimdan chiqdi.')
