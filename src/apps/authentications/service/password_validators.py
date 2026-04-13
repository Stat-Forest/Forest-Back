import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class StrongPasswordValidator:
    """
    Strong password validator:
    - min 8 chars
    - uppercase
    - lowercase
    - digit
    - special char
    - not too similar to user attributes
    """

    def validate(self, password, user=None):
        errors = []

        if len(password) < 8:
            errors.append(_("Parol kamida 8 ta belgidan iborat bo‘lishi kerak."))

        if not re.search(r"[A-Z]", password):
            errors.append(_("Parolda kamida 1 ta katta harf bo‘lishi kerak."))

        if not re.search(r"[a-z]", password):
            errors.append(_("Parolda kamida 1 ta kichik harf bo‘lishi kerak."))

        if not re.search(r"\d", password):
            errors.append(_("Parolda kamida 1 ta raqam bo‘lishi kerak."))

        if not re.search(r"[^\w\s]", password):
            errors.append(_("Parolda kamida 1 ta maxsus belgi bo‘lishi kerak."))

        if user:
            password_lower = password.lower()
            personal_parts = [
                getattr(user, "email", "") or "",
                getattr(user, "first_name", "") or "",
                getattr(user, "last_name", "") or "",
                getattr(user, "phone_number", "") or "",
            ]

            for part in personal_parts:
                part = str(part).strip().lower()
                if not part:
                    continue

                if "@" in part:
                    part = part.split("@")[0]

                if len(part) >= 3 and part in password_lower:
                    errors.append(
                        _("Parol foydalanuvchi ma’lumotlariga juda o‘xshash bo‘lmasligi kerak.")
                    )
                    break

        common_passwords = {
            "123456",
            "12345678",
            "123456789",
            "password",
            "password123",
            "qwerty",
            "qwerty123",
            "admin123",
            "welcome123",
        }

        if password.lower() in common_passwords:
            errors.append(_("Juda sodda parol tanlandi."))

        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _(
            "Parol kamida 8 ta belgidan iborat bo‘lishi, katta-kichik harf, "
            "raqam va maxsus belgi qatnashishi kerak."
        )