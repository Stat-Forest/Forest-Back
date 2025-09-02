from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags


def send_reset_password_email(email, code):
    subject = "Parolni tiklash uchun tasdiqlash kodi"

    html_content = f"""
    <html>
      <body style="font-family:Arial, sans-serif; line-height:1.6; color:#333;">
        <h2 style="color:#2c7be5;">Assalomu alaykum!</h2>

        <p>Sizning <strong>parolni tiklash</strong> so‘rovingiz qabul qilindi.</p>

        <p style="font-size: 18px; margin-top: 20px;">
          🔐 <strong>Tasdiqlash kodingiz:</strong><br>
          <span style="font-size: 24px; background-color:#f1f3f5; padding: 10px 20px; border-radius: 5px; display: inline-block; margin-top: 5px;">
            {code}
          </span>
        </p>

        <p style="margin-top: 30px;">
          Ushbu kod <strong>10 daqiqa</strong> davomida amal qiladi. Agar siz bu so‘rovni yubormagan bo‘lsangiz, iltimos, e’tiborsiz qoldiring.
        </p>

        <p style="margin-top: 40px;">
          Hurmat bilan,<br>
          <strong>ERP tizimi Yordam jamoasi</strong>
        </p>
      </body>
    </html>
    """

    text_content = strip_tags(html_content)

    email_message = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email="tolqinovoybek92@gmail.com",
        to=[email]
    )
    email_message.attach_alternative(html_content, "text/html")
    email_message.send()
