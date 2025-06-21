from django.core.mail import send_mail

def send_reset_password_email(email, code):
    subject = "Parolni tiklash uchun tasdiqlash kodi"
    message = f"""
Assalomu alaykum!

Sizning parolni tiklash so‘rovingiz qabul qilindi.

🔐 Tasdiqlash kodingiz:
    >>> {code} <<<

Ushbu kod 10 daqiqa davomida amal qiladi. Agar siz bu so‘rovni yubormagan bo‘lsangiz, iltimos, e’tiborsiz qoldiring.

Hurmat bilan,
Yordam jamoasi
    """.strip()

    send_mail(
        subject=subject,
        message=message,
        from_email="tolqinovoybek92@gmail.com",
        recipient_list=[email]
    )
