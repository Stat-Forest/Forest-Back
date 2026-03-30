import time
from typing import Any, Dict, List

from .ollama_client_optimized import OllamaClient
from .prompt_builder_optimized import build_prompt, validate_and_format_answer
from .domain_filter import classify_question, detect_language
from .fast_responses import get_fast_response
from .terminology_normalizer import TerminologyNormalizer
from .quality_validator import AnswerQualityValidator
from .fallback_responses import FallbackResponses
from .rag_service_optimized import RAGService
from apps.utils.ai_cache.cache_service import AICacheService
from apps.utils.ai_cache.semantic_cache_service import SemanticCacheService


class AIService:
    def __init__(self) -> None:
        self.client = OllamaClient()
        self.rag = RAGService()

    def ask(self, question: str) -> Dict[str, Any]:
        return self.handle_ai_request(question)

    def _base_response(
        self,
        *,
        answer: str,
        response_time_ms: int,
        llm_time_ms: int = 0,
        rag_time_ms: int = 0,
        cache_hit: bool = False,
        routing_type: str = "direct",
        context_used: int = 0,
        quality_score: float = 1.0,
        quality_issues: List[str] | None = None,
    ) -> Dict[str, Any]:
        return {
            "answer": answer,
            "response_time_ms": response_time_ms,
            "llm_time_ms": llm_time_ms,
            "rag_time_ms": rag_time_ms,
            "cache_hit": cache_hit,
            "routing_type": routing_type,
            "context_used": context_used,
            "quality_score": quality_score,
            "quality_issues": quality_issues or [],
        }

    def _determine_top_k(self, question: str) -> int:
        q = TerminologyNormalizer.normalize_text(question)

        # count/type/structure savollarga ko'proq context kerak
        if any(p in q for p in ["nechta", "qanday bo'lim", "qanday turlari", "farqi"]):
            return 2

        if len(q.split()) <= 12:
            return 1
        if len(q.split()) <= 24:
            return 2
        return 3

    def _can_answer_from_context_directly(self, question: str, context: List[str]) -> bool:
        if not context:
            return False

        q = TerminologyNormalizer.normalize_text(question)

        # structure/count savollarda ba'zan LLM kerak bo'lishi mumkin
        blocked_patterns = [
            "nechta",
            "taqqosla",
            "solishtir",
            "farqini ayt",
        ]
        if any(p in q for p in blocked_patterns):
            return False

        direct_patterns = [
            "nima",
            "qanday",
            "qachon",
            "kim yaratadi",
            "kim yuboradi",
            "qayerda ishlatiladi",
            "nima bo'ladi",
            "qanday ishlaydi",
            "qanday hisoblanadi",
            "qanday yuboriladi",
            "qanday yaratiladi",
        ]
        return any(pattern in q for pattern in direct_patterns)

    def _answer_directly_from_context(self, context: List[str]) -> str:
        if not context:
            return "Bu savol bo'yicha aniq ma'lumot topilmadi."

        if len(context) == 1:
            return validate_and_format_answer(context[0], context)

        merged = " ".join(c.strip() for c in context if c and c.strip())
        return validate_and_format_answer(merged, context)

    def _should_attempt_rag_even_if_offtopic(self, question: str) -> bool:
        normalized = TerminologyNormalizer.normalize_text(question)
        rescue_patterns = [
            "hisobot",
            "muddat",
            "reja",
            "amalda",
            "ustun",
            "tashkilot",
            "urug'",
            "jamg'arma",
            "daromad",
            "ko'chat",
            "nihol",
            "o'simlik",
            "bo'lim",
            "accepted",
            "sent",
            "cancelled",
        ]
        return any(p in normalized for p in rescue_patterns)

    def handle_ai_request(self, question: str) -> Dict[str, Any]:
        start_time = time.time()

        raw_question = (question or "").strip()
        if not raw_question:
            return self._base_response(
                answer="Savol bo'sh bo'lmasligi kerak.",
                response_time_ms=1,
                routing_type="invalid",
                quality_score=0.0,
                quality_issues=["Bo'sh savol"],
            )

        normalized_question = TerminologyNormalizer.normalize_text(raw_question)

        fast_response = get_fast_response(normalized_question)
        if fast_response:
            return self._base_response(
                answer=fast_response,
                response_time_ms=1,
                cache_hit=True,
                routing_type="fast",
            )

        cached_answer = AICacheService.get(normalized_question)
        if cached_answer:
            return self._base_response(
                answer=cached_answer,
                response_time_ms=1,
                cache_hit=True,
                routing_type="cache",
            )

        semantic_answer = SemanticCacheService.get_similar_response(normalized_question)
        if semantic_answer:
            return self._base_response(
                answer=semantic_answer,
                response_time_ms=5,
                cache_hit=True,
                routing_type="semantic_cache",
                quality_score=0.95,
            )

        category = classify_question(normalized_question)
        language = detect_language(normalized_question)

        if category == "greeting":
            answer = (
                "Здравствуйте! Я помогаю по системе Stat-Urmon. Задайте вопрос о создании отчетов, плане или итогах."
                if language == "ru"
                else "Salom! Men Stat-Urmon tizimi bo'yicha yordam beraman. Hisobot, reja, muddat yoki jami haqida savol bering."
            )
            AICacheService.set(normalized_question, answer)
            return self._base_response(
                answer=answer,
                response_time_ms=1,
                routing_type="greeting",
            )

        if category == "meta":
            answer = (
                "Я помогаю по системе Stat-Urmon: отчеты, сроки, планы, фактические значения и общие итоги."
                if language == "ru"
                else "Men Stat-Urmon tizimi bo'yicha yordam beraman: hisobot, muddat, reja, amalda va umumiy jamilar haqida."
            )
            AICacheService.set(normalized_question, answer)
            return self._base_response(
                answer=answer,
                response_time_ms=1,
                routing_type="meta",
            )

        context: List[str] = []
        rag_time_ms = 0
        routing_type = "rag_0"

        should_try_rag = (
            category == "domain"
            or TerminologyNormalizer.is_domain_specific(normalized_question)
            or self._should_attempt_rag_even_if_offtopic(normalized_question)
        )

        if should_try_rag:
            rag_start = time.time()
            top_k = self._determine_top_k(normalized_question)
            context = self.rag.search(normalized_question, top_k=top_k)
            rag_time_ms = int((time.time() - rag_start) * 1000)
            routing_type = f"rag_{top_k}"

        if category == "off_topic" and not context:
            answer = (
                "Пожалуйста, задавайте вопросы только по системе Stat-Urmon."
                if language == "ru"
                else "Iltimos, faqat Stat-Urmon tizimiga oid savol bering."
            )
            return self._base_response(
                answer=answer,
                response_time_ms=int((time.time() - start_time) * 1000),
                rag_time_ms=rag_time_ms,
                routing_type="off_topic",
            )

        if not context and TerminologyNormalizer.is_domain_specific(normalized_question):
            answer = FallbackResponses.get_no_context_response(normalized_question)
            AICacheService.set(normalized_question, answer)
            SemanticCacheService.set_similar_response(normalized_question, answer)

            return self._base_response(
                answer=answer,
                response_time_ms=int((time.time() - start_time) * 1000),
                rag_time_ms=rag_time_ms,
                routing_type="fallback_no_context",
                quality_score=0.7,
                quality_issues=["Kontekst topilmadi"],
            )

        if context and self._can_answer_from_context_directly(normalized_question, context):
            answer = self._answer_directly_from_context(context)

            AICacheService.set(normalized_question, answer)
            SemanticCacheService.set_similar_response(normalized_question, answer)

            return self._base_response(
                answer=answer,
                response_time_ms=int((time.time() - start_time) * 1000),
                llm_time_ms=0,
                rag_time_ms=rag_time_ms,
                routing_type="direct_from_context",
                context_used=len(context),
                quality_score=1.0,
            )

        llm_start = time.time()
        prompt = build_prompt(normalized_question, context)
        raw_answer = self.client.generate(prompt)
        llm_time_ms = int((time.time() - llm_start) * 1000)

        validation = AnswerQualityValidator.comprehensive_validation(raw_answer, context)

        if validation.get("is_valid", False):
            answer = validate_and_format_answer(raw_answer, context)
            quality_score = 1.0
            quality_issues = validation.get("warnings", []) or []
        else:
            if context:
                answer = self._answer_directly_from_context(context)
                quality_score = 0.7
            else:
                answer = FallbackResponses.get_no_context_response(normalized_question)
                quality_score = 0.5

            quality_issues = validation.get("issues", [])

        AICacheService.set(normalized_question, answer)
        SemanticCacheService.set_similar_response(normalized_question, answer)

        response_time_ms = int((time.time() - start_time) * 1000)

        return self._base_response(
            answer=answer,
            response_time_ms=response_time_ms,
            llm_time_ms=llm_time_ms,
            rag_time_ms=rag_time_ms,
            routing_type=routing_type,
            context_used=len(context),
            quality_score=quality_score,
            quality_issues=quality_issues,
        )