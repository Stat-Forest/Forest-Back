from django.core.mail import send_mail

def send_reset_password_email(email, code):
    send_mail(
        subject="Parolni tiklash uchun tasdiqlash kodi",
        message=f"Reset qilish uchun sizning tasdiqlash kodingiz: {code}",
        from_email="tolqinovoybek92@gmail.com",
        recipient_list=[email]
    )