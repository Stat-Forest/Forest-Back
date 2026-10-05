"""
Yuklanadigan fayllar uchun validatorlar.

Kengaytma + faylning birinchi baytlari (magic) tekshiriladi: foydalanuvchi
.html/.svg/.js faylni .pdf deb nomlab yuklay olmaydi. /media/ nginx orqali
to'g'ridan-to'g'ri beriladi, shuning uchun brauzerda bajariladigan fayl
turlariga umuman yo'l qo'yilmaydi.
"""
import os

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # nginx client_max_body_size bilan bir xil

_OLE = (b"\xd0\xcf\x11\xe0",)      # .doc / .xls (OLE2)
_ZIP = (b"PK\x03\x04",)            # .docx / .xlsx (OOXML)

DOCUMENT_TYPES = {
    ".pdf": (b"%PDF",),
    ".doc": _OLE,
    ".docx": _ZIP,
    ".xls": _OLE,
    ".xlsx": _ZIP,
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG",),
}

IMAGE_TYPES = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG",),
    ".webp": (b"RIFF",),
    ".svg": (b"<svg", b"<?xml"),
}


@deconstructible
class FileTypeValidator:
    def __init__(self, allowed: dict, max_size: int = MAX_UPLOAD_SIZE):
        self.allowed = allowed
        self.max_size = max_size

    def __call__(self, value):
        name = getattr(value, "name", "") or ""
        ext = os.path.splitext(name)[1].lower()
        if ext not in self.allowed:
            raise ValidationError(
                _("Ruxsat etilmagan fayl turi: %(ext)s. Mumkin: %(allowed)s"),
                params={"ext": ext or "—", "allowed": ", ".join(sorted(self.allowed))},
            )
        size = getattr(value, "size", None)
        if size is not None and size > self.max_size:
            raise ValidationError(
                _("Fayl hajmi %(mb)s MB dan oshmasligi kerak."),
                params={"mb": self.max_size // (1024 * 1024)},
            )
        # Saqlangan (yopiq) fayl — faqat yangi yuklashda tekshiramiz
        if getattr(value, "closed", False) and not hasattr(value, "read"):
            return
        try:
            value.open("rb")
            head = value.read(16)
            value.seek(0)
        except (OSError, ValueError):
            return
        head_stripped = head.lstrip()
        if not any(head.startswith(m) or head_stripped.startswith(m) for m in self.allowed[ext]):
            raise ValidationError(
                _("Fayl mazmuni %(ext)s formatiga mos kelmaydi."), params={"ext": ext}
            )

    def __eq__(self, other):
        return isinstance(other, FileTypeValidator) and self.allowed == other.allowed and self.max_size == other.max_size


validate_document_file = FileTypeValidator(DOCUMENT_TYPES)
validate_image_file = FileTypeValidator(IMAGE_TYPES, max_size=5 * 1024 * 1024)
