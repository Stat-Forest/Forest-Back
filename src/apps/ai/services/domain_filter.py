import re
import unicodedata
from typing import Literal

# ============================================================
# 1. LANGUAGE DETECTION
# ============================================================

Language = Literal["uz", "ru"]

CYRILLIC_PATTERN = re.compile(r"[а-яА-ЯёЁ]")


def detect_language(text: str) -> Language:
    """
    Tilni aniqlash:
    - Agar kirill harf bo‘lsa → ru
    - Aks holda → uz
    """
    if CYRILLIC_PATTERN.search(text):
        return "ru"
    return "uz"


# ============================================================
# 2. NORMALIZATION
# ============================================================

def normalize_text(text: str) -> str:
    """
    Matnni:
    - unicode normalize
    - kichik harf
    - o'/g' standartlashtirish
    - punctuation olib tashlash
    """
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = text.replace("o'", "o").replace("g'", "g")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ============================================================
# 3. KEYWORD SETLAR
# ============================================================

GREETINGS = {
    "salom",
    "assalomu alaykum",
    "alaykum",
    "salomlar",
    "привет",
    "здравствуйте",
    "здраствуйте",
}

META_QUESTIONS = {
    "nima qila olasan",
    "nimalarni bilasan",
    "qanday savollarga javob berasan",
    "kim san",
    "kimsan",
}

STAT_URMON_KEYWORDS = {
    "hisobot",
    "reja",
    "amalda",
    "foiz",
    "viloyat",
    "respublika",
    "tuman",
    "ormon",
    "kochat",
    "nihol",
    "muddat",
    "jami",
    "yigindi",
    "tashkilot",
    "bolim",
    "qator",
    "eimzo",
    "imzo",
    "kirish",
    "tizim",
}


# ============================================================
# 4. FUZZY MATCH (YAXSHILANGAN)
# ============================================================

def fuzzy_match(word: str, keyword: str) -> bool:
    if word == keyword:
        return True

    if word.startswith(keyword):
        return True

    if keyword in word:
        return True

    # kelishik qo‘shimchalari
    if word.endswith(("ga", "da", "ni", "dan", "lar")):
        base = word[:-2]
        if base == keyword:
            return True

    return False


# ============================================================
# 5. CLASSIFICATION
# ============================================================

Category = Literal["greeting", "meta", "domain", "off_topic"]


def classify_question(question: str) -> Category:
    normalized = normalize_text(question)

    if not normalized:
        return "off_topic"

    # Greeting
    for greeting in GREETINGS:
        if greeting in normalized:
            return "greeting"

    # Meta
    for meta in META_QUESTIONS:
        if meta in normalized:
            return "meta"

    # Domain
    words = normalized.split()

    for word in words:
        for keyword in STAT_URMON_KEYWORDS:
            if fuzzy_match(word, keyword):
                return "domain"

    return "off_topic"
