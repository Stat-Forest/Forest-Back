import logging
from django.core.cache import cache

from .domain_filter import is_stat_urmon_related
from .prompt_builder import build_prompt
from .ollama_client import OllamaClient


logger = logging.getLogger("ai")


class AIService:
    def __init__(self):
        self.client = OllamaClient()

    def ask(self, question: str) -> str:
        logger.info(f"AI Question: {question}")

        if not is_stat_urmon_related(question):
            return "Iltimos, faqat Stat-Urmon ERP tizimiga oid savol bering."

        cache_key = f"ai_answer:{question}"
        cached_answer = cache.get(cache_key)

        if cached_answer:
            return cached_answer

        prompt = build_prompt(question)
        answer = self.client.generate(prompt)

        cache.set(cache_key, answer, timeout=3600)

        return answer