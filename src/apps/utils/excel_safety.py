"""
Yuklangan .xlsx (ZIP) fayl uchun "zip bomb" himoyasi (audit R1).

openpyxl `read_only=False` rejimida sheet XML'ini to'liq xotiraga oladi: 5 MB'lik,
lekin 1000:1 siqilgan fayl bir necha GB ga yoyilib worker'ni o'chiradi. Shu
sababli workbook ochilishidan oldin ZIP yozuvlarining yoyilgan hajmi va siqish
nisbati tekshiriladi.
"""
import zipfile

MAX_UNCOMPRESSED = 60 * 1024 * 1024   # barcha yozuvlar yig'indisi
MAX_RATIO = 200                        # yoyilgan / siqilgan


class UnsafeExcelFile(ValueError):
    pass


def check_xlsx_zip(file_obj, max_uncompressed: int = MAX_UNCOMPRESSED, max_ratio: int = MAX_RATIO) -> None:
    """Xavfli bo'lsa UnsafeExcelFile (ValueError) ko'taradi; fayl ko'rsatkichi boshiga qaytariladi."""
    pos = file_obj.tell() if hasattr(file_obj, "tell") else None
    try:
        try:
            zf = zipfile.ZipFile(file_obj)
        except zipfile.BadZipFile:
            raise UnsafeExcelFile("Fayl .xlsx (ZIP) formatida emas yoki buzilgan.")
        total = 0
        with zf:
            for info in zf.infolist():
                total += info.file_size
                if total > max_uncompressed:
                    raise UnsafeExcelFile("Excel fayl ichki hajmi juda katta.")
                if info.compress_size and info.file_size / max(info.compress_size, 1) > max_ratio and info.file_size > 1024 * 1024:
                    raise UnsafeExcelFile("Excel fayl siqish nisbati shubhali (zip bomb).")
    finally:
        if pos is not None:
            try:
                file_obj.seek(pos)
            except (OSError, ValueError):
                pass
