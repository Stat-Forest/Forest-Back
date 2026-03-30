from typing import Literal

from apps.ai.services.terminology_normalizer import TerminologyNormalizer

Language = Literal["uz", "ru"]


def detect_language(text: str) -> Language:
    normalized = TerminologyNormalizer.normalize_text(text)
    cyrillic_count = sum(1 for ch in normalized if "\u0400" <= ch <= "\u04FF")
    if cyrillic_count > 3:
        return "ru"
    return "uz"


def _contains_greeting(text: str) -> bool:
    greetings = [
        "salom",
        "assalomu alaykum",
        "привет",
        "zdravstvuyte",
    ]
    return any(g in text for g in greetings)


def _contains_meta(text: str) -> bool:
    meta_patterns = [
        "sen kimsan",
        "siz kimsiz",
        "nima yordam bera olasan",
        "nimalarni bilasan",
        "what can you do",
        "who are you",
        "что ты умеешь",
    ]
    return any(p in text for p in meta_patterns)


def classify_question(question: str) -> str:
    normalized = TerminologyNormalizer.normalize_text(question)

    if not normalized:
        return "off_topic"

    domain_signal = TerminologyNormalizer.is_domain_specific(normalized)

    # greeting faqat sof greeting bo'lsa ishlaydi
    if _contains_greeting(normalized) and not domain_signal and len(normalized.split()) <= 3:
        return "greeting"

    if _contains_meta(normalized) and not domain_signal:
        return "meta"

    if domain_signal:
        return "domain"

    soft_domain_patterns = [
        "qanday ishlaydi",
        "qanday yaratiladi",
        "qanday hisoblanadi",
        "qanday yuboriladi",
        "qachon yaratiladi",
        "farqi nima",
        "qabul qilingan",
        "hisoboti",
        "ustun",
        "jadval",
        "tashkilot",
        "hisobot",
        "muddat",
        "reja",
        "statement",
        "deadline",
        "plan",
        "urug'",
        "ko'chat",
        "nihol",
        "daromad",
        "jamg'arma",
    ]
    if any(p in normalized for p in soft_domain_patterns):
        return "domain"

    return "off_topic"