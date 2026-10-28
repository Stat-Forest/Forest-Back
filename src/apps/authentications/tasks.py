from celery import shared_task

from apps.authentications.service.send_reset_password import send_reset_password_email


@shared_task(name="authentications.send_reset_password_email")
def send_reset_password_email_task(email: str, code: str) -> None:
    """Parolni tiklash kodi Celery'da yuboriladi (audit C1): SMTP so'rov ichida
    bo'lsa, javob vaqti email mavjudligini oshkor qilardi."""
    send_reset_password_email(email, code)


@shared_task(name="authentications.flush_expired_tokens", ignore_result=True)
def flush_expired_tokens():
    """simplejwt token_blacklist jadvallarini tozalash (har login/rotatsiya qator qo'shadi)."""
    from django.core.management import call_command
    call_command("flushexpiredtokens")
