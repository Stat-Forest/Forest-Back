from typing import List

from apps.ai.services.domain_filter import detect_language, Language
from apps.ai.services.terminology_normalizer import TerminologyNormalizer


def build_system_prompt(language: Language) -> str:
    if language == "ru":
        return (
            "Ты помощник Stat-Urmon. "
            "Отвечай только по контексту. "
            "Если контекста достаточно, дай полный и точный ответ без выдумок. "
            "Не здоровайся без причины."
        )

    return (
        "Siz Stat-Urmon yordamchisiz. "
        "Faqat kontekst asosida javob bering. "
        "Kontekst yetarli bo'lsa, to'liq va aniq javob bering. "
        "O'zingizdan ma'lumot qo'shmang. "
        "Sababsiz salomlashmang."
    )


def build_prompt(question: str, context: List[str] | None = None) -> str:
    language = detect_language(question)
    normalized_question = TerminologyNormalizer.normalize_text(question)

    context_text = ""
    if context:
        context_text = "\n\n".join((item or "").strip() for item in context if item).strip()
        context_text = context_text[:1500]

    return f"""SYSTEM: {build_system_prompt(language)}
KONTEKST:
{context_text or "Topilmadi"}

SAVOL:
{normalized_question}

QOIDALAR:
1. Faqat kontekstdagi ma'lumotdan foydalaning.
2. Savolga mos to'liq javob bering.
3. Salomlashmang.
4. Kontekstda yo'q ma'lumotni yozmang.

JAVOB:"""


def validate_and_format_answer(answer: str, context: List[str] | None = None) -> str:
    if not answer or not answer.strip():
        return "Bu savol bo'yicha aniq ma'lumot topilmadi."

    answer = " ".join(answer.strip().split())
    answer = answer.replace("o'lim", "bo'lim").replace("O'lim", "Bo'lim")

    if len(answer) > 1200:
        answer = answer[:1200].rsplit(" ", 1)[0].rstrip(",;:") + "..."

    return answer