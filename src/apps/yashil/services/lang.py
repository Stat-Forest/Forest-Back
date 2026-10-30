"""
Modul xabarlari tili (D-28): platforma tili `uz` → o'zbek lotin, `ru` → rus.

Koddagi xabarlar kirillcha (o'zbek) yoziladi; javob chegarasida o'giriladi:
- uz: kirill → lotin transliteratsiya (katalog kerak emas);
- ru: `lang_ru.RU` katalogi; f-string qiymatlari ({0}, {1}) shablon bo'yicha ajratib olinadi.
Hujjat matni (`doc_text`) — alohida: hujjat yaratilgan tilda, `DOC_RU` katalogi, qiymatlar o'girilmaydi.
So'rov tili LocaleMiddleware orqali (`Accept-Language`); fon vazifalari tilni o'zi uzatadi.
"""
import re
from functools import lru_cache

from django.utils import translation

from apps.yashil.services.lang_ru import DOC_RU, RU

UZ, RU_LANG = "uz", "ru"
_CYR = re.compile(r"[Ѐ-ӿ]")
_PH = re.compile(r"\{(\d+)\}")
_VOWELS = set("аеёиоуэюяўАЕЁИОУЭЮЯЎ")
_SIMPLE = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l",
    "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ч": "ch",
    "ш": "sh", "щ": "sh", "ъ": "'", "ь": "", "э": "e", "ё": "yo", "ю": "yu", "я": "ya", "ў": "o'", "қ": "q",
    "ғ": "g'", "ҳ": "h",
}


def current() -> str:
    """Faol so'rov tili: ru yoki uz (boshqa tillar — uz)."""
    code = (translation.get_language() or "").lower()
    return RU_LANG if code.startswith("ru") else UZ


def normalize(code) -> str:
    return RU_LANG if str(code or "").lower().startswith("ru") else UZ


def _is_letter(ch: str) -> bool:
    return bool(ch) and ch.isalpha()


@lru_cache(maxsize=4096)
def to_lat(text: str) -> str:
    """O'zbek kirill → lotin (1995 imlo): е/ц so'z boshida va unlidan keyin, katta harflar saqlanadi."""
    if not text or not _CYR.search(text):
        return text
    out = []
    n = len(text)
    for i, ch in enumerate(text):
        low = ch.lower()
        prev = text[i - 1] if i else ""
        nxt = text[i + 1] if i + 1 < n else ""
        if low == "ъ" and nxt.lower() in "еёюя":
            continue  # объект → obyekt: «y» keyingi harfda bor
        if low == "е":
            lat = "ye" if (not _is_letter(prev) or prev in _VOWELS or prev.lower() in "ъь") else "e"
        elif low == "ц":
            lat = "ts" if prev in _VOWELS else "s"
        elif low in _SIMPLE:
            lat = _SIMPLE[low]
        else:
            out.append(ch)
            continue
        if ch != low and lat:
            # Katta harf: keyingi (yoki oldingi) harf ham katta bo'lsa — butun so'z katta (ШАРТ → SHART)
            whole_upper = (_is_letter(nxt) and nxt.isupper()) or (not _is_letter(nxt) and _is_letter(prev) and prev.isupper())
            lat = lat.upper() if whole_upper else lat[0].upper() + lat[1:]
        out.append(lat)
    return "".join(out)


def _compile(key: str):
    parts = _PH.split(key)
    # split: [lit, idx, lit, idx, ...]
    rx, order = [], []
    for i, part in enumerate(parts):
        if i % 2:
            rx.append("(.*?)")
            order.append(int(part))
        else:
            rx.append(re.escape(part))
    return re.compile("".join(rx) + r"\Z", re.S), order


_TEMPLATES = sorted(
    ((k, *_compile(k)) for k in RU if _PH.search(k)),
    key=lambda t: -len(_PH.sub("", t[0])),  # eng aniq (uzun matnli) shablon birinchi
)


def _match(text: str):
    """(ruscha shablon, qiymatlar) yoki None."""
    if text in RU:
        return RU[text], ()
    for key, rx, order in _TEMPLATES:
        m = rx.match(text)
        if m:
            values = [None] * len(order)
            for pos, idx in enumerate(order):
                values[idx] = m.group(pos + 1)
            return RU[key], tuple(values)
    return None


def _ru_value(value: str) -> str:
    """Shablon ichidagi qiymat: katalogda bo'lsa ruscha, ro'yxat («; », «, ») — har bo'lagi alohida,
    kirillcha nom — lotin, qolgani o'zgarmaydi."""
    hit = _match(value)
    if hit is not None:
        return _fill(*hit)
    for sep in ("; ", ", "):
        if sep in value:
            return sep.join(_ru_value(part) for part in value.split(sep))
    return to_lat(value)


def _fill(template: str, values: tuple) -> str:
    if not values:
        return template
    return _PH.sub(lambda m: _ru_value(values[int(m.group(1))]), template)


@lru_cache(maxsize=8192)
def _tr(text: str, lang: str, known_only: bool) -> str:
    if lang == RU_LANG:
        hit = _match(text)
        if hit is not None:
            return _fill(*hit)
        if "; " in text and not known_only:
            return "; ".join(_tr(part, lang, False) for part in text.split("; "))
        return text
    if known_only and _match(text) is None:
        return text
    return to_lat(text)


def tr(text, lang: str | None = None):
    """Tizim xabari: uz — lotin, ru — katalog bo'yicha (topilmasa o'zgarmaydi)."""
    if not isinstance(text, str) or not text or not _CYR.search(text):
        return text
    return _tr(text, normalize(lang) if lang else current(), False)


def tr_known(text, lang: str | None = None):
    """Faqat katalogdagi tizim matni o'giriladi; foydalanuvchi yozgan matn (izoh, sabab) o'zgarmaydi."""
    if not isinstance(text, str) or not text or not _CYR.search(text):
        return text
    return _tr(text, normalize(lang) if lang else current(), True)


def tr_tree(value, lang: str | None = None, keys: frozenset | None = None):
    """dict/list ichidagi satrlar: `keys` berilsa faqat shu kalitlar ostidagilar."""
    lang = normalize(lang) if lang else current()
    if isinstance(value, dict):
        return {k: (tr_tree(v, lang, None) if keys is None or k in keys else tr_tree(v, lang, keys) if isinstance(v, (dict, list)) else v)
                for k, v in value.items()}
    if isinstance(value, list):
        return [tr_tree(v, lang, keys) for v in value]
    if keys is None and isinstance(value, str):
        return tr(value, lang)
    return value


def doc_text(template: str, doc_lang: str | None = None, *values) -> str:
    """Hujjat matni: `doc_lang` yo'q — eski hujjat (kirill, o'zgarmaydi); uz — lotin; ru — `DOC_RU`/`RU`.
    Qiymatlar ({0}, {1}) o'girilmaydi — ular hujjat tilida tayyorlangan yoki foydalanuvchi matni."""
    if doc_lang == RU_LANG:
        text = DOC_RU.get(template) or RU.get(template, template)
    elif doc_lang == UZ:
        text = to_lat(template)
    else:
        text = template
    if not values:
        return text
    return _PH.sub(lambda m: str(values[int(m.group(1))]), text)
