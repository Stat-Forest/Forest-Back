from typing import Dict, List

from apps.ai.services.terminology_normalizer import TerminologyNormalizer


class AnswerQualityValidator:
    """
    Soft validation.
    Goal: obviously bad answersni ushlash.
    Goal emas: foydali answerlarni yiqitish.
    """

    HALLUCINATION_PATTERNS = [
        "men o'ylayman",
        "taxmin qilaman",
        "ehtimol",
        "bo'lishi mumkin",
        "aniq emas",
        "umuman olganda",
    ]

    @staticmethod
    def validate_grounding(answer: str, context: List[str]) -> tuple[bool, str]:
        if not context:
            return True, ""

        answer_terms = set(TerminologyNormalizer.extract_key_terms(answer))
        if not answer_terms:
            return True, ""

        context_text = " ".join(context)
        context_terms = set(TerminologyNormalizer.extract_key_terms(context_text))

        # Hammasi emas, katta qismi mos kelsa yetadi
        overlap = answer_terms.intersection(context_terms)
        if answer_terms and len(overlap) == 0:
            return False, "Javob terminlari kontekst bilan mos kelmadi"

        return True, ""

    @classmethod
    def detect_hallucination_patterns(cls, answer: str) -> tuple[bool, str]:
        answer_lower = answer.lower()
        for pattern in cls.HALLUCINATION_PATTERNS:
            if pattern in answer_lower:
                return False, f"Noaniq ifoda topildi: {pattern}"
        return True, ""

    @staticmethod
    def check_terminology_consistency(answer: str) -> tuple[bool, str]:
        issues = []

        if "o'lim" in answer.lower():
            issues.append("'o'lim' o'rniga 'bo'lim' ishlatilishi kerak")

        return len(issues) == 0, "; ".join(issues)

    @staticmethod
    def validate_length_and_structure(answer: str) -> tuple[bool, str]:
        text = answer.strip()

        if len(text) < 8:
            return False, "Javob juda qisqa"

        if len(text) > 700:
            return False, "Javob juda uzun"

        return True, ""

    @classmethod
    def comprehensive_validation(cls, answer: str, context: List[str]) -> Dict[str, object]:
        results = {
            "is_valid": True,
            "issues": [],
        }

        checks = [
            cls.validate_grounding(answer, context),
            cls.detect_hallucination_patterns(answer),
            cls.check_terminology_consistency(answer),
            cls.validate_length_and_structure(answer),
        ]

        for ok, msg in checks:
            if not ok:
                results["is_valid"] = False
                results["issues"].append(msg)

        return results