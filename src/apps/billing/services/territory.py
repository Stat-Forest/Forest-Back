"""
Viloyat/tuman kodlari (cs.egov.uz MҲОБТ klassifikatori: viloyat `1708`,
tuman `1708209`) va nomlarni solishtirish uchun normalizatsiya.

Excel'da eski qisqa kodlar ham uchraydi (viloyat `8`, tuman `209`) —
`resolve_region_code` / `resolve_district_code` ikkalasini ham qabul qiladi.
"""
import re

from apps.billing.models import District, Region

_CHAR_MAP = {"қ": "к", "ғ": "г", "ҳ": "х", "ў": "у", "ё": "е", "ъ": "", "ь": "", "-": "", "'": "", "‘": "", "’": ""}
# "тумани"/"туман", "шаҳри"/"шаҳар" — bir joyning ikki shakli; lekin "Нукус тумани"
# va "Нукус шаҳри" — ikki ALOHIDA birlik, shuning uchun qo'shimcha tashlanmaydi,
# kanonik belgiga almashtiriladi.
_SUFFIX_CANON = (("тумани", "|tuman"), ("туман", "|tuman"), ("шахри", "|shahar"), ("шахар", "|shahar"))
_REGION_SUFFIXES = ("вилояти", "республикаси", "республика", "р.")


def normalize_name(name) -> str:
    value = str(name or "").lower().strip()
    value = "".join(_CHAR_MAP.get(ch, ch) for ch in value)
    return re.sub(r"\s+", "", value)


def normalize_region_name(name) -> str:
    value = normalize_name(name)
    for suffix in _REGION_SUFFIXES:
        if value.endswith(suffix):
            return value[: -len(suffix)]
    return value


def normalize_district_name(name) -> str:
    value = normalize_name(name)
    for suffix, tag in _SUFFIX_CANON:
        if value.endswith(suffix):
            return value[: -len(suffix)] + tag
    return value


def _digits(value) -> str:
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def resolve_region_code(code) -> Region | None:
    """`1708` yoki eski qisqa `8`/`08` → Region."""
    code = _digits(code)
    if not code:
        return None
    region = Region.objects.filter(code=code).first()
    if region is None and code.isdigit() and len(code) <= 2:
        region = Region.objects.filter(code=f"17{code.zfill(2)}").first()
    return region


def resolve_district_code(code, region: Region | None) -> District | None:
    """`1708209` yoki viloyat ichidagi qisqa `209` → District."""
    code = _digits(code)
    if not code:
        return None
    districts = District.objects.all()
    if region is not None:
        districts = districts.filter(region=region)
    district = districts.filter(code=code).first()
    if district is None and region is not None and code.isdigit() and len(code) <= 3:
        district = districts.filter(code=f"{region.code}{code.zfill(3)}").first()
    return district
