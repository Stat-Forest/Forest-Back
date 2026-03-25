from apps.ai.services.domain_filter import Language, detect_language


def build_system_prompt(language: Language) -> str:
    if language == "ru":
        return """
Вы помощник системы Stat-Urmon.

Отвечайте ТОЛЬКО на русском языке.
Не используйте английские слова.
Ответ должен быть 4–6 предложений.
Если вопрос не относится к системе:
"Пожалуйста, задавайте вопросы только по системе Stat-Urmon."
"""
    return """
Siz Stat-Urmon tizimining sun’iy yordamchisiz.

Faqat o‘zbek tilida javob bering.
Inglizcha termin ishlatmang.
Javob 4–6 gapdan oshmasin.
Agar savol tizimga tegishli bo‘lmasa:
"Iltimos, faqat Stat-Urmon tizimiga oid savol bering."
"""


# ============================================================
# 7. ERP CONTEXT
# ============================================================

ERP_CONTEXT = """
Stat-Urmon tizimi:
- Hisobotlar muddat asosida yaratiladi.
- Har bir hisobot bo‘lim va qatorlardan iborat.
- Reja — oldindan belgilangan ma’lumot.
- Amalda — bajarilgan natija.
- Viloyat jami — viloyatdagi barcha tashkilot hisobotlari yig‘indisi.
- Respublika jami — barcha viloyatlar yig‘indisi.
"""


# ============================================================
# 8. MAIN PROMPT BUILDER
# ============================================================

def build_prompt(user_question: str) -> str:
    language = detect_language(user_question)
    system_prompt = build_system_prompt(language)

    return f"""
{system_prompt}

Tizim haqida:
{ERP_CONTEXT}

Savol:
{user_question}

Javob:
"""