from apps.ai.services.terminology_normalizer import TerminologyNormalizer


class FallbackResponses:
    @staticmethod
    def get_no_context_response(question: str) -> str:
        normalized = TerminologyNormalizer.normalize_text(question)
        key_terms = TerminologyNormalizer.extract_key_terms(normalized)

        if "muddat" in key_terms:
            return "Muddat — hisobot topshirish uchun belgilangan vaqt oralig'i."

        if "hisobot" in key_terms:
            return "Hisobot — tizimdagi ma'lumotlarni kiritish va topshirish uchun yaratiladigan hujjat."

        if "reja" in key_terms:
            return "Reja — oldindan belgilangan ko'rsatkich yoki qiymat."

        if "amalda" in key_terms:
            return "Amalda — haqiqatda bajarilgan natija yoki fakt qiymati."

        if "bo'lim" in key_terms:
            return "Bo'lim — tashkilot ichidagi tarkibiy qism bo'lib, hisobot jarayonida o'z roliga ega."

        if "viloyat" in key_terms:
            return "Viloyat jami — viloyatdagi tashkilotlar hisobotlari asosida shakllanadigan umumiy yig'indi."

        if "respublika" in key_terms:
            return "Respublika jami — barcha hududlar bo'yicha umumlashtirilgan yakuniy yig'indi."

        return (
            "Bu savol bo'yicha aniq kontekst topilmadi. "
            "Iltimos, Stat-Urmon tizimi bo'yicha savolni aniqroq yozing."
        )

    @staticmethod
    def get_uncertain_response() -> str:
        return "Kechirasiz, bu savol bo'yicha aniq javobni kontekstdan topa olmadim."

    @staticmethod
    def get_hallucination_detected_response() -> str:
        return "Kechirasiz, javobni tekshirishda nomuvofiqlik aniqlandi. Iltimos, savolni boshqacha yozib bering."