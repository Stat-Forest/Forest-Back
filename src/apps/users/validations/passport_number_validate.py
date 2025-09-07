import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_passport_number(value):
    if not re.match(r'^[A-Z]{2}\d{7}$', value):
        raise ValidationError(_("format number of password incorrect. For Example: AA 1234567"))


def validate_jshshr(value):
    """
    JSHSHR: 14 xonali faqat raqamlardan iborat bo‘lishi kerak
    """
    if not re.match(r'^\d{14}$', value):
        raise ValidationError(_("JSHSHR must contain exactly 14 digits"))