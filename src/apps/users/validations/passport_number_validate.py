import re
from django.utils.translation import gettext_lazy as _

from apps.base.exceptions.exception_files import CustomExceptionError


def validate_passport_number(value):
    if not re.match(r'^[A-Z]{2}\d{7}$', value):
        raise CustomExceptionError(code=400, detail=_("format number of password incorrect. For Example: AA 1234567"))


def validate_jshshr(value):
    """
    JSHSHR: 14 xonali faqat raqamlardan iborat bo‘lishi kerak
    """
    if not re.match(r'^\d{14}$', value):
        raise CustomExceptionError(code=400, detail=_("JSHSHR must contain exactly 14 digits"))