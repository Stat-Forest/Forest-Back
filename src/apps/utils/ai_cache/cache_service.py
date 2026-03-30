import hashlib
from django.core.cache import cache


class AICacheService:

    PREFIX = "ai_answer"

    @classmethod
    def make_key(cls, question: str) -> str:
        normalized = question.strip().lower()
        hashed = hashlib.md5(normalized.encode()).hexdigest()
        return f"{cls.PREFIX}:{hashed}"

    @classmethod
    def get(cls, question: str):
        key = cls.make_key(question)
        return cache.get(key)

    @classmethod
    def set(cls, question: str, answer: str, timeout=60 * 60 * 24):
        key = cls.make_key(question)
        cache.set(key, answer, timeout=timeout)